package com.example.chatgptassistant

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import retrofit2.*
import retrofit2.converter.gson.GsonConverterFactory

class MainActivity : AppCompatActivity() {
    private lateinit var inputText: EditText
    private lateinit var outputText: TextView
    private lateinit var sendButton: Button
    private val api: ChatGPTApi by lazy {
        Retrofit.Builder()
            .baseUrl("https://api.openai.com/v1/")
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ChatGPTApi::class.java)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        inputText = findViewById(R.id.inputText)
        outputText = findViewById(R.id.outputText)
        sendButton = findViewById(R.id.sendButton)

        sendButton.setOnClickListener {
            val prompt = inputText.text.toString()
            sendMessageToChatGPT(prompt)
        }
    }

    private fun sendMessageToChatGPT(prompt: String) {
        val call = api.getChatGPTResponse(
            "Bearer YOUR_API_KEY",
            ChatGPTRequest(prompt)
        )
        call.enqueue(object : Callback<ChatGPTResponse> {
            override fun onResponse(call: Call<ChatGPTResponse>, response: Response<ChatGPTResponse>) {
                if (response.isSuccessful) {
                    val reply = response.body()?.choices?.first()?.text
                    outputText.text = reply
                } else {
                    outputText.text = "Error: ${response.code()}"
                }
            }

            override fun onFailure(call: Call<ChatGPTResponse>, t: Throwable) {
                outputText.text = "Failed to connect to ChatGPT"
            }
        })
    }
}
