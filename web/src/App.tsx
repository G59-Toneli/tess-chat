import { Route, Routes } from 'react-router'
import { AppLayout } from '@/layout/AppLayout'
import { Chat } from '@/pages/Chat'
import { Compartilhados } from '@/pages/Compartilhados'
import { Compartilhamento } from '@/pages/Compartilhamento'
import { Login } from '@/pages/Login'
import { Placeholder } from '@/pages/Placeholder'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/s/:shareId" element={<Compartilhamento />} />
      <Route element={<AppLayout />}>
        <Route path="/" element={<Chat />} />
        <Route path="/c/:id" element={<Chat />} />
        <Route path="/config" element={<Placeholder titulo="Configuração" />} />
        <Route path="/auditoria" element={<Placeholder titulo="Auditoria" />} />
        <Route path="/creditos" element={<Placeholder titulo="Créditos" />} />
        <Route path="/tools" element={<Placeholder titulo="Tools" />} />
        <Route path="/mcp" element={<Placeholder titulo="Servidores MCP" />} />
        <Route path="/conectores" element={<Placeholder titulo="Conectores" />} />
        <Route path="/compartilhados" element={<Compartilhados />} />
        <Route path="/perfil" element={<Placeholder titulo="Perfil" />} />
        <Route path="/admin" element={<Placeholder titulo="Administração" />} />
        <Route path="*" element={<Placeholder titulo="Página não encontrada" />} />
      </Route>
    </Routes>
  )
}
