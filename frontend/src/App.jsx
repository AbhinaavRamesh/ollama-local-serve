import { Routes, Route, Navigate } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import Layout from './components/common/Layout';
import Overview from './pages/Overview';
import Performance from './pages/Performance';
import Logs from './pages/Logs';
import Models from './pages/Models';
import Settings from './pages/Settings';
import System from './pages/System';

function App() {
  return (
    <Layout>
      <AnimatePresence mode="wait">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/system" element={<System />} />
          <Route path="/performance" element={<Performance />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/models" element={<Models />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AnimatePresence>
    </Layout>
  );
}

export default App;
