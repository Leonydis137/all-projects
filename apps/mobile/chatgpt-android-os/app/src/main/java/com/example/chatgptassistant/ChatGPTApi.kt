package com.example.chatgptassistant

import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.POST

interface ChatGPTApi {
    @POST("completions")
    fun getChatGPTResponse(
        @Header("Authorization") auth: String,
        @Body request: ChatGPTRequest
    ): Call<ChatGPTResponse>
}
