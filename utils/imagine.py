import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def imagine(prompt, size="1024x1024"):
    """
    Generates an image from a prompt using OpenAI's DALL·E model.
    Returns the image URL or an error message.
    """
    try:
        response = openai.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size=size
        )
        return response.data[0].url
    except Exception as e:
        return f"Image generation error: {str(e)}"
