import { Route, Routes } from 'react-router'
import { AppLayout } from '@/layout/AppLayout'
import { Admin } from '@/pages/Admin'
import { Auditoria } from '@/pages/Auditoria'
import { Chat } from '@/pages/Chat'
import { Compartilhados } from '@/pages/Compartilhados'
import { Compartilhamento } from '@/pages/Compartilhamento'
import { Conectores } from '@/pages/Conectores'
import { Configuracao } from '@/pages/Configuracao'
import { Creditos } from '@/pages/Creditos'
import { Login } from '@/pages/Login'
import { Mcp } from '@/pages/Mcp'
import { NaoEncontrada, Placeholder } from '@/pages/Placeholder'
import { Tools } from '@/pages/Tools'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/s/:shareId" element={<Compartilhamento />} />
      <Route element={<AppLayout />}>
        <Route path="/" element={<Chat />} />
        <Route path="/c/:id" element={<Chat />} />
        <Route path="/config" element={<Configuracao />} />
        <Route path="/auditoria" element={<Auditoria />} />
        <Route path="/creditos" element={<Creditos />} />
        <Route path="/tools" element={<Tools />} />
        <Route path="/mcp" element={<Mcp />} />
        <Route path="/conectores" element={<Conectores />} />
        <Route path="/compartilhados" element={<Compartilhados />} />
        <Route path="/perfil" element={<Placeholder titulo="Perfil" />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="*" element={<NaoEncontrada />} />
      </Route>
    </Routes>
  )
}
