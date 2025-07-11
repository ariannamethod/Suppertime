import openai
import os
import time
import random
from openai import OpenAI

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def imagine(prompt, size="1024x1024"):
    """
    Generates an image from a prompt using OpenAI's DALL·E model.
    Returns the image URL or an error message.
    
    Args:
        prompt (str): Description of the image to generate
        size (str): Size of the image, one of: "1024x1024", "1024x1792", "1792x1024"
        
    Returns:
        str: The URL of the generated image or an error message
    """
    try:
        # Enhance the prompt to make it more detailed
        enhanced_prompt = enhance_prompt(prompt)
        
        # Add retry logic for robustness
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=enhanced_prompt,
                    n=1,
                    size=size
                )
                return response.data[0].url
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise e
                time.sleep(2)  # Wait before retrying
                
    except Exception as e:
        return f"Image generation error: {str(e)}"

def enhance_prompt(prompt):
    """
    Enhances the drawing prompt to get better results from DALL-E.
    
    Args:
        prompt (str): Original user prompt
        
    Returns:
        str: Enhanced prompt with more details and style instructions
    """
    # List of artistic style enhancements to randomly choose from
    style_enhancements = [
        "in a surreal, dreamlike style",
        "with vibrant, saturated colors",
        "using dramatic chiaroscuro lighting",
        "in a minimalist, abstract composition",
        "with intricate, detailed texturing",
        "using a moody, atmospheric palette",
        "with impressionist brush strokes",
        "in a dystopian, dark setting",
        "with ethereal, glowing elements",
        "using bold, geometric patterns",
    ]
    
    # Don't enhance if it already seems detailed enough
    if len(prompt.split()) > 15:
        return prompt
    
    # Randomly choose a style enhancement
    enhancement = random.choice(style_enhancements)
    
    # Check if prompt already ends with punctuation
    if prompt[-1] in ".!?":
        enhanced_prompt = f"{prompt} Create this {enhancement}."
    else:
        enhanced_prompt = f"{prompt}. Create this {enhancement}."
    
    return enhanced_prompt
