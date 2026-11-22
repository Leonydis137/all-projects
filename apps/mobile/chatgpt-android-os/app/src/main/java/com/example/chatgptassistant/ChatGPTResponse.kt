package com.example.chatgptassistant

data class ChatGPTResponse(
    val choices: List<Choice>
)

data class Choice(
    val text: String
)
