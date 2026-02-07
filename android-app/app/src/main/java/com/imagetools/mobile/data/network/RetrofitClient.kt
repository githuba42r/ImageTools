package com.imagetools.mobile.data.network

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Singleton object for Retrofit client
 */
object RetrofitClient {
    
    private var retrofit: Retrofit? = null
    private var baseUrl: String = ""
    
    /**
     * Initialize or update the Retrofit client with a new base URL
     */
    fun setBaseUrl(url: String) {
        // Ensure URL ends with /
        baseUrl = if (url.endsWith("/")) url else "$url/"
        retrofit = null // Force recreation with new URL
    }
    
    /**
     * Get the Retrofit instance
     */
    private fun getRetrofit(): Retrofit {
        if (retrofit == null || baseUrl.isEmpty()) {
            if (baseUrl.isEmpty()) {
                throw IllegalStateException("Base URL not set. Call setBaseUrl() first.")
            }
            
            val loggingInterceptor = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }
            
            val client = OkHttpClient.Builder()
                .addInterceptor(loggingInterceptor)
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .writeTimeout(30, TimeUnit.SECONDS)
                .build()
            
            retrofit = Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
        }
        
        return retrofit!!
    }
    
    /**
     * Get the API interface
     */
    fun getApi(): ImageToolsApi {
        return getRetrofit().create(ImageToolsApi::class.java)
    }
}
