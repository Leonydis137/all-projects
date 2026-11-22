package com.example.chatgptassistant

data class ChatGPTRequest(
    val prompt: String,
    val max_tokens: Int = 100,
    val model: String = "text-davinci-003"
)
