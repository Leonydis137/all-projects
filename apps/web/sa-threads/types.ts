
export interface Product {
  id: number;
  name: string;
  brand: string;
  price: number;
  imageUrl: string;
  category: 'Men' | 'Women' | 'Sports';
  description: string;
}

export interface CartItem extends Product {
  quantity: number;
}

export interface ChatMessage {
  role: 'user' | 'model';
  text: string;
}
