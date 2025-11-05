import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { ProductList } from './components/ProductList';
import { CartView } from './components/CartView';
import { CheckoutModal } from './components/CheckoutModal';
import { ProductDetailModal } from './components/ProductDetailModal';
import { RecommendedProducts } from './components/RecommendedProducts';
import { ChatBot } from './components/ChatBot';
import { Footer } from './components/Footer';
import { Toast } from './components/Toast';
import { useCart } from './hooks/useCart';
import { Product } from './types';
import { ALL_PRODUCTS } from './constants';
import { performSmartSearch, performVisualSearch } from './services/geminiService';

type Category = 'All' | 'Men' | 'Women' | 'Sports';

const ChatIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
  </svg>
);

const App: React.FC = () => {
    const { cart, addToCart, removeFromCart, updateQuantity, clearCart } = useCart();
    const [products, setProducts] = useState<Product[]>(ALL_PRODUCTS);
    const [isLoading, setIsLoading] = useState(false);
    const [activeCategory, setActiveCategory] = useState<Category>('All');
    
    // Modal states
    const [isCartOpen, setIsCartOpen] = useState(false);
    const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);
    const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

    // Chat states
    const [isChatOpen, setIsChatOpen] = useState(false);
    const [chatContext, setChatContext] = useState<Product | null>(null);

    // Toast state
    const [toastMessage, setToastMessage] = useState('');
    const [showToast, setShowToast] = useState(false);

    const triggerToast = (message: string) => {
        setToastMessage(message);
        setShowToast(true);
        setTimeout(() => setShowToast(false), 3000);
    };

    const handleCategorySelect = (category: Category) => {
        setActiveCategory(category);
        if (category === 'All') {
            setProducts(ALL_PRODUCTS);
        } else {
            setProducts(ALL_PRODUCTS.filter(p => p.category === category));
        }
    };

    const handleSearch = async (query: string, isSmart: boolean = false) => {
        setIsLoading(true);
        if (!query.trim()) {
            handleCategorySelect(activeCategory); // Reset to current category filter
            setIsLoading(false);
            return;
        }

        if (isSmart) {
            triggerToast('Using AI Smart Search...');
            const results = await performSmartSearch(query, ALL_PRODUCTS);
            setProducts(results);
            setActiveCategory('All'); // Reset category filter on search
        } else {
            // Simple instant search
            const lowerCaseQuery = query.toLowerCase();
            const filtered = ALL_PRODUCTS.filter(p =>
                p.name.toLowerCase().includes(lowerCaseQuery) ||
                p.brand.toLowerCase().includes(lowerCaseQuery)
            );
            setProducts(filtered);
            setActiveCategory('All');
        }
        setIsLoading(false);
    };
    
    const handleVisualSearch = async (file: File) => {
        setIsLoading(true);
        triggerToast('Analyzing image with AI...');
        try {
            const results = await performVisualSearch(file, ALL_PRODUCTS);
            setProducts(results);
            setActiveCategory('All');
        } catch (error) {
            console.error("Visual search failed", error);
            triggerToast("Sorry, we couldn't analyze that image.");
        }
        setIsLoading(false);
    };

    const handleAddToCart = (product: Product, quantity: number = 1) => {
        addToCart(product, quantity);
        if (!isCartOpen) {
            triggerToast(`${product.name} added to cart!`);
        }
    };

    const handleOrderPlaced = () => {
        clearCart();
        setIsCheckoutOpen(false);
        // The success message is shown in the checkout modal itself.
    };
    
    const handleAskAssistant = (product: Product) => {
        setChatContext(product);
        setIsChatOpen(true);
        setSelectedProduct(null); // Close modal when opening chat
    };

    const handleChatClose = () => {
        setIsChatOpen(false);
        setChatContext(null); // Clear context when chat is closed
    };
    
    useEffect(() => {
        // Prevent body scroll when a modal or chat is open
        if (isCartOpen || isCheckoutOpen || selectedProduct || isChatOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = 'auto';
        }
        return () => { document.body.style.overflow = 'auto'; };
    }, [isCartOpen, isCheckoutOpen, selectedProduct, isChatOpen]);

    return (
        <div className="flex flex-col min-h-screen bg-gray-50 text-brand-primary font-sans">
            <Header 
                cartCount={cart.reduce((sum, item) => sum + item.quantity, 0)}
                onCartClick={() => setIsCartOpen(true)}
                onSearch={handleSearch}
                onVisualSearch={handleVisualSearch}
                onCategorySelect={handleCategorySelect}
                activeCategory={activeCategory}
            />
            <main className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-grow">
                <ProductList
                    products={products}
                    onAddToCart={handleAddToCart}
                    onProductSelect={setSelectedProduct}
                    isLoading={isLoading}
                    triggerToast={triggerToast}
                />
                 <RecommendedProducts
                    cartItems={cart}
                    allProducts={ALL_PRODUCTS}
                    onAddToCart={handleAddToCart}
                    onProductSelect={setSelectedProduct}
                    triggerToast={triggerToast}
                />
            </main>
            <Footer />
            
            <CartView
                isOpen={isCartOpen}
                onClose={() => setIsCartOpen(false)}
                cartItems={cart}
                onRemove={removeFromCart}
                onUpdateQuantity={updateQuantity}
                onCheckout={() => {
                    setIsCartOpen(false);
                    setIsCheckoutOpen(true);
                }}
            />
            
            <CheckoutModal
                isOpen={isCheckoutOpen}
                onClose={() => setIsCheckoutOpen(false)}
                cartItems={cart}
                onOrderPlaced={handleOrderPlaced}
            />
            
            <ProductDetailModal
                product={selectedProduct}
                isOpen={!!selectedProduct}
                onClose={() => setSelectedProduct(null)}
                onAddToCart={handleAddToCart}
                triggerToast={triggerToast}
                onAskAssistant={handleAskAssistant}
            />

            <ChatBot
                isOpen={isChatOpen}
                onClose={handleChatClose}
                context={chatContext}
                products={ALL_PRODUCTS}
                onAddToCart={handleAddToCart}
                triggerToast={triggerToast}
            />
            
            <Toast message={toastMessage} show={showToast} />

            {/* ChatBot Floating Action Button */}
            {!isChatOpen && (
                <button
                    onClick={() => {
                        setChatContext(null);
                        setIsChatOpen(true);
                    }}
                    className="fixed bottom-6 right-6 bg-brand-primary text-white w-16 h-16 rounded-full shadow-lg flex items-center justify-center hover:bg-brand-accent transition-all duration-300 z-50 animate-fade-in"
                    aria-label="Open chatbot"
                >
                    <ChatIcon />
                </button>
            )}
        </div>
    );
};

export default App;