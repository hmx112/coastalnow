import React from 'react';
import { createRoot } from 'react-dom/client';
import { TDSMobileAITProvider } from '@toss/tds-mobile-ait';
import App from './App.jsx';
import './styles.css';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <TDSMobileAITProvider>
      <App />
    </TDSMobileAITProvider>
  </React.StrictMode>
);
