import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useUser } from '@/context/UserContext';
import axios from 'axios';
import toast from 'react-hot-toast';

export const UserAuthModal = () => {
  const { isAuthenticated, setUser } = useUser();
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async () => {
    if (!email) return toast.error('Please enter an email to log in.');
    setIsLoading(true);
    try {
      const response = await axios.get(`http://localhost:8000/api/v1/user?email=${email}`);
      setUser({ fullName: response.data.full_name, email: response.data.email });
      toast.success(`Welcome back, ${response.data.full_name}!`);
    } catch (error: any) {
      toast.error(error.response?.status === 404 ? 'User not found. Please sign up.' : 'Login failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignUp = async () => {
    if (!email || !fullName) return toast.error('Email and Full Name are required.');
    setIsLoading(true);
    try {
      const response = await axios.post('http://localhost:8000/api/v1/user', { email, full_name: fullName });
      setUser({ fullName: response.data.full_name, email: response.data.email });
      toast.success(`Welcome, ${response.data.full_name}!`);
    } catch (error) {
      toast.error('Sign up failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={!isAuthenticated}>
      <DialogContent className="sm:max-w-[425px]" onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle>Welcome to Okada AI Agent</DialogTitle>
          <DialogDescription>Please log in or sign up to begin.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="email" className="text-right">Email</Label>
            <Input id="email" value={email} onChange={(e) => setEmail(e.target.value)} className="col-span-3" />
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="name" className="text-right">Full Name</Label>
            <Input id="name" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="(Required for sign up)" className="col-span-3" />
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={handleLogin} disabled={isLoading}>{isLoading ? '...' : 'Login'}</Button>
          <Button onClick={handleSignUp} disabled={isLoading}>{isLoading ? '...' : 'Sign Up'}</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
