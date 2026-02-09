package com.imagetools.mobile.data.network

import com.imagetools.mobile.data.models.ImageUploadRequest
import com.imagetools.mobile.data.models.ImageUploadResponse
import com.imagetools.mobile.data.models.UnpairResponse
import com.imagetools.mobile.data.models.ValidateAuthRequest
import com.imagetools.mobile.data.models.ValidateSecretRequest
import com.imagetools.mobile.data.models.ValidateSecretResponse
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

/**
 * Retrofit API interface for Image Tools backend
 */
interface ImageToolsApi {
    
    @POST("api/v1/mobile/validate-secret")
    suspend fun validateSecret(
        @Body request: ValidateSecretRequest
    ): Response<ValidateSecretResponse>
    
    @Multipart
    @POST("api/v1/mobile/upload")
    suspend fun uploadImage(
        @Part("long_term_secret") longTermSecret: RequestBody,
        @Part file: MultipartBody.Part
    ): Response<ImageUploadResponse>
    
    @POST("api/v1/mobile/unpair")
    suspend fun unpairDevice(
        @Body request: ValidateAuthRequest
    ): Response<UnpairResponse>
}
