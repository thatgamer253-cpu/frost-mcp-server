-- 1. Users Table: Core profile and auth data
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    profile_picture_url TEXT,
    bio TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Posts Table: User-generated content
CREATE TABLE IF NOT EXISTS posts (
    post_id SERIAL PRIMARY KEY,
    author_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    content_text TEXT,
    media_url TEXT, -- Link to images/videos in S3/Cloudflare R2
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Connections Table: Many-to-Many follower relationships
CREATE TABLE IF NOT EXISTS connections (
    follower_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    following_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (follower_id, following_id) -- Ensures unique relationships
);

-- 4. Feed Items Cache: Pre-building timelines for performance
CREATE TABLE IF NOT EXISTS feed_cache (
    user_id INT REFERENCES users(user_id),
    post_id INT REFERENCES posts(post_id),
    rank_score FLOAT, -- For algorithmic sorting
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
