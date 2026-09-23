// Dados mock locais. Nenhuma chamada à API neste ticket.

export type ConversaMock = { id: string; titulo: string }
export type MensagemMock = { id: string; role: 'user' | 'assistant'; texto: string }

export const usuarioMock = { nome: 'Usuário Demo', email: 'demo@exemplo.com' }

export const conversasMock: ConversaMock[] = [
  { id: '1', titulo: 'Resumo do contrato' },
  { id: '2', titulo: 'Ideias para o README' },
  { id: '3', titulo: 'Análise de PDF' },
]

export const mensagensMock: Record<string, MensagemMock[]> = {
  '1': [
    { id: 'm1', role: 'user', texto: 'Resume o contrato em 3 pontos.' },
    { id: 'm2', role: 'assistant', texto: '**Mock.** 1. Prazo de 12 meses. 2. Multa de 10%. 3. Foro em SP.' },
  ],
}
