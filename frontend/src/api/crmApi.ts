// Replacement for frontend/src/api/crmApi.ts
    import apiClient from './client'; // Use your existing axios client

    // We only need the create user function for the demo
    export async function createUser(user: { email: string; password?: string; full_name: string; phone_number?: string }) {
      // The endpoint is /user, not /crm/create_user
      const res = await apiClient.post('/user', user);
      if (res.status !== 200) throw new Error('Failed to create user');
      return res.data;
    }

    // The sign-in logic will use the GET /user endpoint
    export async function signInUser({ email }: { email: string; }) {
      const res = await apiClient.get(`/user?email=${email}`);
      if (res.status !== 200) throw new Error('Failed to sign in');
      return res.data;
    }