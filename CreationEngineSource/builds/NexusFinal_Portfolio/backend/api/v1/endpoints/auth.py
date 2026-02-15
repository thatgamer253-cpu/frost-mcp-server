{user_in.email}")
        existing_user = await crud_user.get_by_email(db, email=user_in.email)
        if existing_user:
            logger.warning(f"Registration failed: User with email '{user_in.email}' already exists.")
            raise DetailedHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The user with this email already exists in the system.",
                error_code="USER_ALREADY_EXISTS"
            )

        hashed_password = get_password_hash(user_in.password)
        user_create_data = user_in.model_dump()
        user_create_data["hashed_password"] = hashed_password
        del user_create_data["password"]  # Remove plain password before passing to CRUD

        user = await crud_user.create(db, obj_in=user_create_data)
        logger.info(f"User registered successfully: {user.email}")

        # Optional: Add a background task for welcome email, logging, or other post-registration actions
        # background_tasks.add_task(send_welcome_email, user.email)

        return user
    except DetailedHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during user registration for email '{user_in.email}': {e}", exc_info=True)
        raise DetailedHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration.",
            error_code="REGISTRATION_FAILED"
        )


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    OAuth2 compatible token login. Authenticates a user and returns access and refresh tokens.

    - **username**: User's email address.
    - **password**: User's password.
    """
    try:
        user = await crud_user.get_by_email(db, email=form_data.username)
        if not user or not verify_password(form_data.password, user.hashed_password):
            logger.warning(f"Failed login attempt for email: {form_data.username}")
            raise DetailedHTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
                error_code="INVALID_CREDENTIALS"
            )

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        access_token = create_access_token(
            data={"sub": user.email, "user_id": str(user.id)}, expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(
            data={"sub": user.email, "user_id": str(user.id)}, expires_delta=refresh_token_expires
        )

        logger.info(f"User logged in successfully: {user.email}")
        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")
    except DetailedHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during user login for email '{form_data.username}': {e}", exc_info=True)
        raise DetailedHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login.",
            error_code="LOGIN_FAILED"
        )


@router.post("/refresh-token", response_model=Token)
async def refresh_access_token(
    token_refresh_request: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Refreshes an access token using a valid refresh token.
    The refresh token itself is not renewed, only a new access token is issued.
    """
    try:
        payload = decode_token(token_refresh_request.refresh_token)
        if payload is None:
            logger.warning("Invalid refresh token provided or token expired.")
            raise DetailedHTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
                error_code="INVALID_REFRESH_TOKEN"
            )

        user_id = payload.get("user_id")
        if not user_id:
            logger.warning("Refresh token payload missing user_id.")
            raise DetailedHTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token payload",
                headers={"WWW-Authenticate": "Bearer"},
                error_code="INVALID_REFRESH_TOKEN_PAYLOAD"
            )

        user = await crud_user.get(db, id=user_id)
        if not user:
            logger.warning(f"User not found for refresh token with user_id: {user_id}")
            raise DetailedHTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found for refresh token",
                headers={"WWW-Authenticate": "Bearer"},
                error_code="USER_NOT_FOUND_FOR_REFRESH"
            )

        # Generate a new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(
            data={"sub": user.email, "user_id": str(user.id)}, expires_delta=access_token_expires
        )

        logger.info(f"Access token refreshed for user: {user.email}")
        return Token(access_token=new_access_token, refresh_token=token_refresh_request.refresh_token, token_type="bearer")
    except DetailedHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during token refresh: {e}", exc_info=True)
        raise DetailedHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during token refresh.",
            error_code="TOKEN_REFRESH_FAILED"
        )


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: UserResponse = Depends(get_current_active_user)
) -> Any:
    """
    Retrieve current authenticated user's details.
    Requires a valid access token in the Authorization header.
    """
    try:
        logger.debug(f"Fetching current user details for '{current_user.email}'")
        return current_user
    except DetailedHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching current user details for '{current_user.email}': {e}