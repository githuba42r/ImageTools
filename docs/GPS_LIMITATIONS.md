# GPS Extraction Limitations on Android

## Overview

Starting with Android 10 (API 29), Google introduced **Scoped Storage** which includes privacy protections that automatically strip GPS/location metadata from images when they are shared between apps.

## The Problem

When another app shares an image to ImageTools via Android's share intent (`ACTION_SEND`), the GPS EXIF data is **stripped by the sending app** before ImageTools receives the image. This is a deliberate privacy protection by Android, not a bug.

### Why This Happens

1. **Privacy by default**: Android assumes users don't want to share their location data when sharing photos
2. **Scoped Storage**: Apps can only access files they created or that the user explicitly grants access to
3. **Content URI redaction**: When apps provide `content://` URIs via share intents, Android automatically redacts sensitive metadata including GPS coordinates

## What ImageTools Attempts

When receiving a shared image, ImageTools tries multiple methods to extract GPS data:

1. **MediaStore lookup by filename**: Search the device's own MediaStore for an image with the same filename/size, then use our `ACCESS_MEDIA_LOCATION` permission to read GPS
2. **Direct MediaStore query**: Query the shared URI for latitude/longitude columns (deprecated but may work on some devices)
3. **File path extraction**: Get the real file path and read EXIF directly (blocked on Android 10+)
4. **setRequireOriginal()**: Request the original unredacted file (only works for URIs we control)
5. **Regular ExifInterface**: Standard EXIF read as fallback

### When GPS Extraction Works

- Images **taken by this device** and stored in the local gallery
- Images where the filename matches an existing MediaStore entry with GPS data
- Older Android versions (pre-Android 10) where scoped storage doesn't apply

### When GPS Extraction Fails

- Images synced from cloud services (Google Photos, iCloud, etc.)
- Screenshots and downloaded images (never had GPS)
- Images shared from apps that process/compress images before sharing
- Images where the MediaStore lookup finds no matching entry

## Recommended Workaround

For reliable GPS preservation, users can:

1. **Use ImageTools' built-in camera** (if implemented) to capture photos directly
2. **Pick images from gallery** within ImageTools (planned feature) instead of sharing from another app
3. **Share original files** using a file manager instead of gallery apps (some file managers preserve metadata)

## Technical Details

### Android Permissions

ImageTools declares these permissions for GPS access:

```xml
<uses-permission android:name="android.permission.ACCESS_MEDIA_LOCATION" />
<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" /> <!-- Android 13+ -->
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"
    android:maxSdkVersion="32" />
```

### The `ACCESS_MEDIA_LOCATION` Permission

This permission allows reading GPS from MediaStore entries, but only when:
- The app initiates the MediaStore query itself
- The URI being read is from the device's own MediaStore (not a shared `content://` URI from another app)

### Relevant Android Documentation

- [Access media location permission](https://developer.android.com/training/data-storage/shared/media#location-info-photos)
- [Scoped storage](https://developer.android.com/about/versions/11/privacy/storage)
- [Photo picker](https://developer.android.com/training/data-storage/shared/photopicker)

## Future Improvements

A "Pick from Gallery" feature is planned which would allow users to select images directly within ImageTools. Since ImageTools would initiate the MediaStore query, the `ACCESS_MEDIA_LOCATION` permission would apply and GPS data should be preserved.
