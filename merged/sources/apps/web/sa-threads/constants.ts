import { Product } from './types';

export const ALL_PRODUCTS: Product[] = [
  {
    id: 1,
    name: 'Air Max 90',
    brand: 'Nike',
    price: 2499.99,
    imageUrl: 'https://images.unsplash.com/photo-1606107557195-0e29a4b5b4aa?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1000&q=80',
    category: 'Men',
    description: 'A classic sneaker that offers timeless style and all-day comfort with its iconic waffle outsole and stitched overlays.'
  },
  {
    id: 2,
    name: 'Superstar Shoes',
    brand: 'Adidas',
    price: 1799.99,
    imageUrl: 'https://images.unsplash.com/photo-1552346154-21d32810aba3?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1170&q=80',
    category: 'Men',
    description: 'The iconic shell-toe sneaker, a staple of hip-hop culture and streetwear fashion for over 50 years.'
  },
  {
    id: 3,
    name: 'Air Jordan 1 Mid',
    brand: 'Jordan',
    price: 2999.99,
    imageUrl: 'https://images.unsplash.com/photo-1612181341019-a1952d3a3915?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=870&q=80',
    category: 'Men',
    description: 'Inspired by the original AJ1, this mid-top edition maintains the iconic look with a mix of premium materials.'
  },
  {
    id: 4,
    name: '501 Original Fit Jeans',
    brand: 'Levis',
    price: 1299.99,
    imageUrl: 'https://images.unsplash.com/photo-1602293589914-9e2964a781d9?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=774&q=80',
    category: 'Men',
    description: 'The original blue jean since 1873. A timeless straight-leg fit that has defined generations.'
  },
  {
    id: 5,
    name: 'D-Strukt Slim Jeans',
    brand: 'Diesel',
    price: 3499.99,
    imageUrl: 'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=774&q=80',
    category: 'Men',
    description: 'A modern slim fit with a comfortable silhouette, crafted from premium stretch denim for a perfect fit.'
  },
  {
    id: 6,
    name: '222 Banda Anniston Track Jacket',
    brand: 'Kappa',
    price: 999.99,
    imageUrl: 'https://images.unsplash.com/photo-1594217983617-0a1864b4e2bb?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=870&q=80',
    category: 'Men',
    description: 'Iconic sportswear jacket featuring the signature Omini logo tape down the sleeves for a retro look.'
  },
  {
    id: 7,
    name: 'Tech Fleece Windrunner',
    brand: 'Nike',
    price: 1999.99,
    imageUrl: 'https://images.unsplash.com/photo-1551537482-f2075a1d7184?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=774&q=80',
    category: 'Women',
    description: 'Lightweight warmth and a modern, tailored fit make this hoodie a versatile essential for any wardrobe.'
  },
  {
    id: 8,
    name: 'Ultraboost 22',
    brand: 'Adidas',
    price: 3299.99,
    imageUrl: 'https://images.unsplash.com/photo-1597405445840-0f834a4d9c17?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=774&q=80',
    category: 'Women',
    description: 'Experience incredible energy return and cushioning with the Ultraboost, designed specifically for the female foot.'
  },
   {
    id: 9,
    name: 'Dri-FIT Training Tee',
    brand: 'Nike',
    price: 599.99,
    imageUrl: 'https://images.unsplash.com/photo-1591195853828-11db59a44f6b?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=774&q=80',
    category: 'Sports',
    description: 'Stay dry and comfortable during your toughest workouts with Nike Dri-FIT fabric that wicks sweat away.'
  },
   {
    id: 10,
    name: 'Tiro 23 Training Pants',
    brand: 'Adidas',
    price: 899.99,
    imageUrl: 'https://images.unsplash.com/photo-1628129288279-4081c7452d2b?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=774&q=80',
    category: 'Sports',
    description: 'Slim-fitting training pants with moisture-absorbing AEROREADY technology and convenient ankle zips.'
  },
   {
    id: 11,
    name: 'High-Waisted Leggings',
    brand: 'Levis',
    price: 799.99,
    imageUrl: 'https://images.unsplash.com/photo-1617422154182-359a34b41a3e?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=870&q=80',
    category: 'Women',
    description: 'Sculpting and comfortable, these high-waisted leggings from Levis offer a flattering fit for everyday wear.'
  },
   {
    id: 12,
    name: 'Air Jordan 1 Low',
    brand: 'Jordan',
    price: 2199.99,
    imageUrl: 'https://images.unsplash.com/photo-1608231387042-89d0ac72c83a?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1000&q=80',
    category: 'Women',
    description: 'The classic Jordan 1 silhouette in a low-top version, perfect for a clean, casual look.'
  },
];