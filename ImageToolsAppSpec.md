I would like create a dockerized container for image tools that allow the upload of images and the the manipulation of the images

the main app should function like imgcompress (GitHub: karimz1/imgcompress) and use an image editor https://ui.toast.com/tui-image-editor

the primary goal of the app is to take images captured on a phone camera (high res and large resolution and file size) and resize and compress them for inclusion in an email or website

it would also be nice to add the ability to use AI to remove the background, and manipulate the images (add filters, stylized etc) and use openroute.ai for the LLM model use. For the AI integration add the oAuth2 PCKE api key retreive from the operators existing openrouter.au account

The tool should not store images long term, but rather simply store the image data locally while manipulating the images.

mulitple image upload must be supported

the app will show a list of uploaded images, and a edit button to use the image edit, an background removal button to use AI (if enabled) to remove the background, button to resize and compress (to common size/bit depth/resolution for email and web) and an button to open an AI chatbot style interface that will show the image and allow a char interface for the AI LLM to manipulate the image


Frontend development in VueJS
Backend development in Pyhton
an database use a local SQLite3 if requried

the app will required no authentication, it will be hosted behind an Traefik and Authelia if published to the internet

the tool should be quick and simple to use, so that the operator can drag and drop image onto the app, click a button to resize for email embedding, or click a button to remove the background and then download the created images

Ensure that there is an undo button on each manilpulation stage to allow the operator to undo the last change.

add a button to download each individual image following modification, and button to copy the image to the clipboard, and a button for the images current loaded to download as a ZIP file

ensure that the tools can be run locally for development/testing, and use a .env .env.local .env.development etc for configuration parameters and settings

the production app will be deployed in Docker and hosted behing a reverse proxy

include Architectural and implementation documentation, a project Readme, and installation Guide, a Developer Guide outlining local development and a Operator User Guide

you can make use of Git already initialized in the project folder to commit stages during development and implemenation