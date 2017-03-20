from flask import Flask
from twilio.rest import TwilioRestClient
from SimpleCV import Image, Blob

import numpy as np
import json
import boto3

app = Flask(__name__)

testImageUrl = "https://s3.amazonaws.com/mms-image-ingest/incoming/telephone-number/coins2.png"
s3BucketUrl = "https://s3.amazonaws.com/mms-image-ingest/incoming/telephone-number/{0}"

@app.route('/')
def usage():
  usageStr = "<html><head><title>Coin Counter Usage</title><h1>Coin Counter</h1></head><body><p><b>Usage:</b><br/><em>countme-test</em>: Runs a test on the image at this url: <a href='{0}'>Test image</a><br/><em>countme&#47;<i>image-url</i></em>: Counts the coins in the image passed as image-url<br/></p></body></html>".format(testImageUrl)
  return usageStr

@app.route('/countme/<input_str>')
def count_me(input_str):
    processUrl = s3BucketUrl.format(input_str)
    print "Processing image at: {0}".format(processUrl)
    try:
        value = process_image(processUrl)
    except:
        print "Cannot read image at: {0}".format(processUrl)
        value = "Bad Image"
    return value

@app.route('/countme-test/')
def coin_count():
    return process_image(testImageUrl)

# The value of the coins in order of their size
# First dim: size of coin
# Second dim: value of the coin
# http://www.usmint.gov/about_the_mint/?action=coin_specifications
coin_diameter_values = np.array([
[ 19.05, 0.01],
[ 21.21, 0.05],
[ 17.91, 0.10],
[ 24.26, 0.25]]);

# put your Twilio credentials here
ACCOUNT_SID = "---"
AUTH_TOKEN = "----"

client = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)
s3 = boto3.client('s3')

#Run it in a python 2.7 environment to test

def process_image(image_url):
        # Print the url for image that is being processed.
        print "Processing image: {}".format(image_url)

        # Construct the Image object from the image URL
        img = Image(image_url)

        # Find the coin blobs from the image after inverting the image
        coins = img.invert().findBlobs(minsize = 500)

        # Use a quarter to calibrate the largest coin in the coin blobs.
        # Logic:
        # coin_diameter_values[3,0] is the size of the US Mint Quarter.
        # Find the largest radius of all the coins in the image. This will be our reference Quarter.
        # usmint_quarter/radius_of_our_quarter will provide the calibration factor.
        # In other words: convert pixels to millimeter.
        px2mm = coin_diameter_values[3,0] / max([c.radius()*2 for c in coins])

        # Initialize index & total value
        i=0
        value = 0.0

        # For each blob in the coins blob list
        for c in coins:
            i=i+1
            # Find the diameter of this coin blob & normalize to the calibration factor
            # ie., find the diameter in millimeter of this coin.
            diameter_in_mm = c.radius() * 2 * px2mm
            # Get an array of values for difference between this coin and all the US Mint coins.
            distance = np.abs(diameter_in_mm - coin_diameter_values[:,0])
            #print "Coin diameter: " , diameter_in_mm, " Distance: ", distance
            # Find the coin with the smallest difference. This is our best guess on the coin type.
            index = np.where(distance == np.min(distance))[0][0]
            # Get the value of the coin and add it to the total amount
            coinValue = coin_diameter_values[index, 1]
            value += coinValue

        message = "The total value of the coins is ${0}".format(value)
        print message
            #coinImg = c.crop()
            #coinImg.drawText(str(coinValue))
            #coinImg.save("Results/coin"+str(i)+".png")
        return "{}".format(value)

def send_sms(message):
    client.messages.create(
        to = "+telephone-number",
        from_= "+telephone-number",
    	body=message)
    print "SMS Message sent"

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))
    # Get the bucket and key from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    # Construct the URL for the image
    image_url = "https://s3.amazonaws.com/{0}/{1}".format(bucket, key)
    # Construct the Image object from the image URL
    img = Image(image_url)
    # Process image
    message = process_image(image_url)
    return message

#process_image(imageurl)


if __name__ == '__main__':
  app.run()
