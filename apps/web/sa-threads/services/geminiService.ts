import { GoogleGenAI, GenerateContentResponse, Part, Chat } from "@google/genai";
import { Product, CartItem, ChatMessage } from '../types';

// Per guidelines, initialize with a named parameter
const ai = new GoogleGenAI({apiKey: process.env.API_KEY});

// Helper function to convert File to base64 Part
const fileToGenerativePart = async (file: File): Promise<Part> => {
  const base64EncodedDataPromise = new Promise<string>((resolve) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve((reader.result as string).split(',')[1]);
    reader.readAsDataURL(file);
  });
  return {
    inlineData: { data: await base64EncodedDataPromise, mimeType: file.type },
  };
};


export const getRecommendations = async (cartItems: CartItem[], allProducts: Product[]): Promise<string> => {
  if (cartItems.length === 0) {
    return "";
  }
  
  const model = 'gemini-2.5-flash';
  
  const cartDetails = cartItems.map(item => `${item.brand} ${item.name}`).join(', ');
  const productList = allProducts.map(p => `${p.brand} ${p.name}`).join('; ');

  const prompt = `Based on these items in the user's cart: [${cartDetails}], and this full list of available products: [${productList}], recommend up to 4 other products. Only return a comma-separated list of the full product names (brand and name), like "Nike Air Max 90, Adidas Superstar Shoes". Do not add any other text or explanation.`;
  
  try {
    const response = await ai.models.generateContent({
        model: model,
        contents: prompt,
    });
    // Per guidelines, access text directly from response.text
    return response.text;
  } catch (error) {
      console.error("Error fetching recommendations from Gemini API:", error);
      throw error;
  }
};

export const performSmartSearch = async (query: string, allProducts: Product[]): Promise<Product[]> => {
    const model = 'gemini-2.5-flash';
    const productList = JSON.stringify(allProducts.map(p => ({id: p.id, name: p.name, brand: p.brand, category: p.category, description: p.description})));

    const prompt = `From the following list of products: ${productList}, find the products that best match the user's search query: "${query}". Respond with only a JSON array of the product IDs that match, for example: [1, 5, 8]. If no products match, return an empty array [].`;
    
    try {
        const response = await ai.models.generateContent({
            model: model,
            contents: prompt,
            config: {
                responseMimeType: 'application/json',
            }
        });
        
        // Per guidelines, access text directly and parse
        const responseText = response.text.trim();
        // Clean up potential markdown code fences around JSON
        const jsonString = responseText.replace(/^```json\s*|```$/g, '');
        const productIds = JSON.parse(jsonString);

        if (Array.isArray(productIds)) {
            return allProducts.filter(p => productIds.includes(p.id));
        }
        return [];

    } catch(error) {
        console.error("Error performing smart search with Gemini API:", error);
        // Fallback to simple text search
        const lowerCaseQuery = query.toLowerCase();
        return allProducts.filter(p => 
            p.name.toLowerCase().includes(lowerCaseQuery) ||
            p.brand.toLowerCase().includes(lowerCaseQuery) ||
            p.description.toLowerCase().includes(lowerCaseQuery)
        );
    }
};

export const performVisualSearch = async (imageFile: File, allProducts: Product[]): Promise<Product[]> => {
    // Correct model for image input
    const model = 'gemini-2.5-flash'; 
    const productList = JSON.stringify(allProducts.map(p => ({id: p.id, name: p.name, brand: p.brand, category: p.category, description: p.description})));

    const imagePart = await fileToGenerativePart(imageFile);
    
    const contents = {
        parts: [
            imagePart,
            { text: `From the following list of products: ${productList}, identify which products are visually similar to the one in the image. Consider style, color, and type. Respond with only a JSON array of the product IDs that are a good match, for example: [3, 12]. If no products match, return an empty array [].` }
        ]
    };
    
    try {
        const response = await ai.models.generateContent({
            model: model,
            contents: contents,
            config: {
                responseMimeType: 'application/json',
            }
        });
        
        // Per guidelines, access text directly and parse
        const responseText = response.text.trim();
        // Clean up potential markdown code fences around JSON
        const jsonString = responseText.replace(/^```json\s*|```$/g, '');
        const productIds = JSON.parse(jsonString);
        
        if (Array.isArray(productIds)) {
            return allProducts.filter(p => productIds.includes(p.id));
        }
        return [];

    } catch(error) {
        console.error("Error performing visual search with Gemini API:", error);
        return []; // Return empty on error
    }
}
