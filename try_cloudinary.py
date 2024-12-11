# post an image to cloudinary and get the url
import cloudinary
import cloudinary.uploader
import cloudinary.api
import requests
import credentials
import json
import os

def post_image_to_cloudinary(image_path):
    cloudinary.config(
        cloud_name = credentials.CLOUDINARY_CLOUD_NAME,
        api_key = credentials.CLOUDINARY_API_KEY,
        api_secret = credentials.CLOUDINARY_API_SECRET,
        secure=True
    )
    response = cloudinary.uploader.upload(image_path)
    return response["url"]

print (post_image_to_cloudinary(r".\avion.png"))