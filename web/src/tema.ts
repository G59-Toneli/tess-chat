// Tema claro/escuro. Dark é o padrão (docs/UI-GUIA.md).

export function temaEscuro(): boolean {
  return document.documentElement.classList.contains('dark')
}

export function alternarTema(): void {
  const escuro = document.documentElement.classList.toggle('dark')
  try {
    localStorage.setItem('tema', escuro ? 'dark' : 'light')
  } catch {
    // Sem storage: o tema vale só nesta aba.
  }
}
