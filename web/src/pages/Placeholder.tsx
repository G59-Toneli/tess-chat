import { useSearchParams } from 'react-router'
import { EstadoCarregando, EstadoErro, EstadoVazio } from '@/components/estados'

/**
 * Tela placeholder até o ticket da funcionalidade.
 * `?estado=carregando|erro` simula os outros estados; o padrão é vazio.
 */
export function Placeholder({ titulo }: { titulo: string }) {
  const [params, setParams] = useSearchParams()
  const estado = params.get('estado')
  return (
    <div className="mx-auto max-w-4xl p-8">
      <h1 className="mb-6 text-2xl font-semibold">{titulo}</h1>
      {estado === 'carregando' ? (
        <EstadoCarregando />
      ) : estado === 'erro' ? (
        <EstadoErro mensagem="Não foi possível carregar os dados (mock)." onTentarDeNovo={() => setParams({})} />
      ) : (
        <EstadoVazio titulo="Nada por aqui ainda" descricao="Esta tela chega num próximo ticket." />
      )}
    </div>
  )
}
