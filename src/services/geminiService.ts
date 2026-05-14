import { GoogleGenAI } from "@google/genai";

let genAI: GoogleGenAI | null = null;

function getGenAI() {
  if (!genAI) {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      throw new Error("GEMINI_API_KEY is not defined in environment variables.");
    }
    genAI = new GoogleGenAI({ apiKey });
  }
  return genAI;
}

export async function getChatResponse(
  message: string, 
  history: { role: 'user' | 'model'; parts: { text: string }[] }[],
  systemInstruction?: string
) {
  try {
    const ai = getGenAI();
    
    const response = await ai.models.generateContent({
      model: "gemini-3-flash-preview",
      contents: [
        ...history,
        { role: 'user', parts: [{ text: message }] }
      ],
      config: {
        systemInstruction: systemInstruction || "You are a specialized AI agent in a high-security neural network. Your tone is professional, technical, and slightly futuristic/cybernetic. Keep responses concise."
      }
    });

    return response.text || "Error: Neural link disrupted. Empty response.";
  } catch (error) {
    console.error("[GeminiService] Error:", error);
    return "Error: Neural link disrupted. Could not process directive.";
  }
}
