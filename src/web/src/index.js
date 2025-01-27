import 'core-js/full';
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { BrowserRouter } from 'react-router-dom';
import { shifu } from 'Service/Shifu.js';
import 'Utils/pollyfill.js';
import 'ShiNiang/index.js';


const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <BrowserRouter>
    <App />
  </BrowserRouter>
);

if (window.shifuPlugins) {
  for (const plugin of window.shifuPlugins) {
    shifu.installPlugin(plugin);
  }
}
