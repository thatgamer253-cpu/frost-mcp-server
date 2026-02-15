from PIL import Image, ImageFilter
import io

def apply_style_filter(image_data, user_input):
    """
    Applies a South Park style filter to the given image data.

    Args:
        image_data (bytes): The binary content of the image to be styled.
        user_input (dict): Additional user input that might affect styling.

    Returns:
        bytes: The binary content of the styled image.
    """
    try:
        # Load the image from bytes
        image = Image.open(io.BytesIO(image_data))

        # Apply a cartoon-like filter
        # This is a placeholder for a more complex South Park style filter
        styled_image = image.convert("RGB").filter(ImageFilter.EDGE_ENHANCE_MORE)

        # Convert the styled image back to bytes
        output = io.BytesIO()
        styled_image.save(output, format='PNG')
        styled_image_data = output.getvalue()

        return styled_image_data

    except Exception as e:
        print(f"Failed to apply style filter: {e}")
        return image_data  # Return the original image data in case of failure