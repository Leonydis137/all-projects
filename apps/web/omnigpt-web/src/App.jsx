import { useState } from "react";
import { askOmniGPT } from "./services/api";

export default function App() {
  const [input, setInput] = useState("");
  const [response, setResponse] = useState("How can I assist you today?");
  const [loading, setLoading] = useState(false);

 const handleSubmit = async () => {
    if (!input.trim()) return;
    setLoading(true);
    const answer = await askOmniGPT(input, "user-001");
    setResponse(answer);
    setInput("");
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6 flex flex-col items-center justify-center">
      <h1 className="text-3xl font-bold mb-6">OmniGPT Assistant</h1>
      <textarea
        className="w-full max-w-xl p-4 text-black rounded resize-none"
        rows={4}
        value={input}
        placeholder="Ask me anything..."
        onChange={(e) => setInput(e.target.value)}
      />
      <button
        className="mt-4 px-6 py-2 bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
        onClick={handleSubmit}
        disabled={loading}
      >
        {loading ? "Thinking..." : "Ask OmniGPT"}
      </button>
      <div className="mt-8 max-w-xl bg-gray-800 p-4 rounded">{response}</div>
    </div>
  );
}
