import React, { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import {
  createBrowserRouter,
  createRoutesFromElements,
  Route,
  RouterProvider
} from 'react-router-dom';

import './index.css';
// IMPORT THE PROVIDER
import { WalletProvider } from './context/WalletContext';

import Layout from './Layout';
import Home from './pages/Home';
import Prediction from './pages/Prediction';
import Room from './pages/Room';

// 1. Define your routes
const router = createBrowserRouter(
  createRoutesFromElements(
    <Route path="/" element={<Layout />}>
      <Route index element={<Home />} />
      <Route path="prediction" element={<Prediction />} />
      <Route path="room/:id" element={<Room />} />
    </Route>
  )
);

// 2. Wrap the RouterProvider inside WalletProvider
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <WalletProvider>
      <RouterProvider router={router} />
    </WalletProvider>
  </StrictMode>
);