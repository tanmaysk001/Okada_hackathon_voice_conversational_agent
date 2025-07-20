
import React from 'react';
import { HeroSection } from '@/components/ui/hero-section-5';




const Index = ({ setUser }: { setUser: (user: any) => void }) => {
  return (
    <div className="min-h-screen bg-background">
      <HeroSection setUser={setUser} />
      
      
      
    </div>
  );
};

export default Index;
