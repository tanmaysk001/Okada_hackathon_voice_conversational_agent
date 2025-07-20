'use client'
import React from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { Menu, X, ChevronRight } from 'lucide-react'
import { useScroll, motion } from 'framer-motion'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { AnimatedText } from '@/components/ui/animated-text'
import { useNavigate } from 'react-router-dom';
import { createUser } from '@/api/crmApi';
import { useState } from 'react';
import { signInUser } from '@/api/crmApi';

export function HeroSection({ setUser }: { setUser: (user: any) => void }) {
    const navigate = useNavigate();
    return (
        <>
            <HeroHeader setUser={setUser} />
            <main className="overflow-x-hidden">
                <section>
                    <div className="py-16 md:pb-24 lg:pb-32 lg:pt-48">
                        <div className="relative z-10 mx-auto flex max-w-7xl flex-col px-6 lg:block lg:px-12">
                            <div className="mx-auto max-w-lg text-center lg:ml-0 lg:max-w-full lg:text-left">
                                <AnimatedText>
                                    <h1 className="mt-4 max-w-2xl text-balance text-5xl md:text-6xl lg:mt-8 xl:text-7xl font-bold">
                                        <span className="word-animate" data-delay="0">Okada</span>{' '}
                                        <span className="word-animate" data-delay="200">IntelliAgent:</span>{' '}
                                        <span className="text-primary word-animate" data-delay="400">Chat.</span>{' '}
                                        <span className="text-primary word-animate" data-delay="600">Choose.</span>{' '}
                                        <span className="text-primary word-animate" data-delay="800">Move</span>{' '}
                                        <span className="text-primary word-animate" data-delay="1000">In.</span>
                                    </h1>
                                </AnimatedText>
                                <p className="mt-6 max-w-2xl text-balance text-lg text-muted-foreground">
                                    AI-powered property assistant that understands your needs, recommends perfect matches, and handles everything from search to scheduling.
                                </p>

                                <div className="mt-8 flex flex-col items-center justify-center gap-2 sm:flex-row lg:justify-start">
                                    <Button
                                        size="lg"
                                        className="h-12 rounded-full pl-5 pr-3 text-base"
                                        onClick={() => navigate('/dashboard')}
                                    >
                                        <span className="text-nowrap">Dashboard</span>
                                        <ChevronRight className="ml-1" />
                                    </Button>
                                    <Button
                                        size="lg"
                                        variant="ghost"
                                        className="h-12 rounded-full px-5 text-base hover:bg-zinc-950/5 dark:hover:bg-white/5">
                                        <span className="text-nowrap">Request Demo</span>
                                    </Button>
                                </div>
                            </div>
                        </div>
                        <div className="aspect-[2/3] absolute inset-1 overflow-hidden rounded-3xl border border-black/10 sm:aspect-video lg:rounded-[3rem] dark:border-white/5">
                            <div 
                                className="size-full bg-cover bg-center opacity-50 dark:opacity-50"
                                style={{
                                    backgroundImage: "url('new-york-skyline-5.jpg')"
                                }}
                            />
                        </div>
                    </div>
                </section>
            </main>
        </>
    )
}

const menuItems = [
    { name: 'Features', href: '#features' },

]

function SignUpDialog({ setUser }: { setUser: (user: any) => void }) {
    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [phone, setPhone] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    return (
        <Dialog>
            <DialogTrigger asChild>
                <Button size="sm">
                    <span>Sign Up</span>
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Create Your Account</DialogTitle>
                    <DialogDescription>
                        Join Okada IntelliAgent and start finding your perfect property today.
                    </DialogDescription>
                </DialogHeader>
                <form
                  onSubmit={async (e) => {
                    e.preventDefault();
                    setLoading(true);
                    setError('');
                    setSuccess('');
                    try {
                      const user = await createUser({ email, password, fullName });
                      setSuccess('Account created! You can now sign in.');
                      setUser(user); // Set user in app state
                      setFullName(''); setEmail(''); setPassword(''); setPhone('');
                    } catch (err) {
                      setError(err instanceof Error ? err.message : 'Signup failed');
                    } finally {
                      setLoading(false);
                    }
                  }}
                >
                  <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                      <Label htmlFor="fullName" className="text-right">
                        Full Name
                      </Label>
                      <Input
                        id="fullName"
                        placeholder="John Doe"
                        className="col-span-3"
                        value={fullName}
                        onChange={e => setFullName(e.target.value)}
                      />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                      <Label htmlFor="email" className="text-right">
                        Email
                      </Label>
                      <Input
                        id="email"
                        type="email"
                        placeholder="john@example.com"
                        className="col-span-3"
                        value={email}
                        onChange={e => setEmail(e.target.value)}
                      />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                      <Label htmlFor="password" className="text-right">
                        Password
                      </Label>
                      <Input
                        id="password"
                        type="password"
                        placeholder="••••••••"
                        className="col-span-3"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                      />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                      <Label htmlFor="phone" className="text-right">
                        Phone
                      </Label>
                      <Input
                        id="phone"
                        placeholder="+1 (555) 123-4567"
                        className="col-span-3"
                        value={phone}
                        onChange={e => setPhone(e.target.value)}
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button type="submit" className="w-full" disabled={loading}>
                      {loading ? 'Creating...' : 'Create Account'}
                    </Button>
                  </DialogFooter>
                  {error && <div className="text-red-500 text-sm mt-2">{error}</div>}
                  {success && <div className="text-green-600 text-sm mt-2">{success}</div>}
                </form>
            </DialogContent>
        </Dialog>
    )
}

function SignInDialog({ setUser }: { setUser: (user: any) => void }) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    return (
        <Dialog>
            <DialogTrigger asChild>
                <Button variant="outline" size="sm">
                    <span>Sign In</span>
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Welcome Back</DialogTitle>
                    <DialogDescription>
                        Sign in to your Okada IntelliAgent account to continue your property search.
                    </DialogDescription>
                </DialogHeader>
                <form
                  onSubmit={async (e) => {
                    e.preventDefault();
                    setLoading(true);
                    setError('');
                    setSuccess('');
                    try {
                      const user = await signInUser({ email, password });
                      setSuccess('Signed in!');
                      setUser(user); // Set user in app state
                      setEmail(''); setPassword('');
                    } catch (err) {
                      setError(err instanceof Error ? err.message : 'Sign in failed');
                    } finally {
                      setLoading(false);
                    }
                  }}
                >
                  <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="loginEmail" className="text-right">
                            Email
                        </Label>
                        <Input
                            id="loginEmail"
                            type="email"
                            placeholder="john@example.com"
                            className="col-span-3"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                        />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="loginPassword" className="text-right">
                            Password
                        </Label>
                        <Input
                            id="loginPassword"
                            type="password"
                            placeholder="••••••••"
                            className="col-span-3"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                        />
                    </div>
                  </div>
                  <DialogFooter className="flex-col space-y-2">
                    <Button type="submit" className="w-full" disabled={loading}>
                      {loading ? 'Signing in...' : 'Sign In'}
                    </Button>
                    <Button variant="link" className="text-sm">
                        Forgot your password?
                    </Button>
                  </DialogFooter>
                  {error && <div className="text-red-500 text-sm mt-2">{error}</div>}
                  {success && <div className="text-green-600 text-sm mt-2">{success}</div>}
                </form>
            </DialogContent>
        </Dialog>
    )
}

const HeroHeader = ({ setUser }: { setUser: (user: any) => void }) => {
    const [menuState, setMenuState] = React.useState(false)
    const [scrolled, setScrolled] = React.useState(false)
    const { scrollYProgress } = useScroll()

    React.useEffect(() => {
        const unsubscribe = scrollYProgress.on('change', (latest) => {
            setScrolled(latest > 0.05)
        })
        return () => unsubscribe()
    }, [scrollYProgress])

    return (
        <header>
            <nav
                data-state={menuState && 'active'}
                className="group fixed z-20 w-full pt-2">
                <div className={cn('mx-auto max-w-7xl rounded-3xl px-6 transition-all duration-300 lg:px-12', scrolled && 'bg-background/80 backdrop-blur-2xl border border-border/50')}>
                    <motion.div
                        key={1}
                        className={cn('relative flex flex-wrap items-center justify-between gap-6 py-3 duration-200 lg:gap-0 lg:py-6', scrolled && 'lg:py-4')}>
                        <div className="flex w-full items-center justify-between gap-12 lg:w-auto">
                            <div className="flex items-center space-x-2">
                                <Logo />
                                <span className="font-bold text-lg">Okada IntelliAgent</span>
                            </div>

                            <button
                                onClick={() => setMenuState(!menuState)}
                                aria-label={menuState == true ? 'Close Menu' : 'Open Menu'}
                                className="relative z-20 -m-2.5 -mr-4 block cursor-pointer p-2.5 lg:hidden">
                                <Menu className="group-data-[state=active]:rotate-180 group-data-[state=active]:scale-0 group-data-[state=active]:opacity-0 m-auto size-6 duration-200" />
                                <X className="group-data-[state=active]:rotate-0 group-data-[state=active]:scale-100 group-data-[state=active]:opacity-100 absolute inset-0 m-auto size-6 -rotate-180 scale-0 opacity-0 duration-200" />
                            </button>

                            <div className="hidden lg:block">
                                <ul className="flex gap-8 text-sm">
                                    {menuItems.map((item, index) => (
                                        <li key={index}>
                                            <a
                                                href={item.href}
                                                className="text-muted-foreground hover:text-accent-foreground block duration-150">
                                                <span>{item.name}</span>
                                            </a>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        <div className="bg-background group-data-[state=active]:block lg:group-data-[state=active]:flex mb-6 hidden w-full flex-wrap items-center justify-end space-y-8 rounded-3xl border p-6 shadow-2xl shadow-zinc-300/20 md:flex-nowrap lg:m-0 lg:flex lg:w-fit lg:gap-6 lg:space-y-0 lg:border-transparent lg:bg-transparent lg:p-0 lg:shadow-none dark:shadow-none dark:lg:bg-transparent">
                            <div className="lg:hidden">
                                <ul className="space-y-6 text-base">
                                    {menuItems.map((item, index) => (
                                        <li key={index}>
                                            <a
                                                href={item.href}
                                                className="text-muted-foreground hover:text-accent-foreground block duration-150">
                                                <span>{item.name}</span>
                                            </a>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                            <div className="flex w-full flex-col space-y-3 sm:flex-row sm:gap-3 sm:space-y-0 md:w-fit">
                                <SignInDialog setUser={setUser} />
                                <SignUpDialog setUser={setUser} />
                            </div>
                        </div>
                    </motion.div>
                </div>
            </nav>
        </header>
    )
}

const Logo = ({ className }: { className?: string }) => {
    return (
        <svg
            viewBox="0 0 40 40"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className={cn('h-8 w-8', className)}>
            <rect width="40" height="40" rx="8" fill="url(#logo-gradient)" />
            <path
                d="M12 28V12h4l4 8 4-8h4v16h-3V17l-3 6h-2l-3-6v11h-3z"
                fill="white"
            />
            <defs>
                <linearGradient
                    id="logo-gradient"
                    x1="0"
                    y1="0"
                    x2="40"
                    y2="40"
                    gradientUnits="userSpaceOnUse">
                    <stop stopColor="#3B82F6" />
                    <stop offset="1" stopColor="#1D4ED8" />
                </linearGradient>
            </defs>
        </svg>
    )
}


