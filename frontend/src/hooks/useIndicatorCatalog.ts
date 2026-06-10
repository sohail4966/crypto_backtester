import { useQuery } from '@tanstack/react-query'
import { fetchIndicatorCatalog } from '@/services/chartDataAdapter'

export function useIndicatorCatalog() {
  return useQuery({
    queryKey: ['indicators', 'catalog'],
    queryFn: fetchIndicatorCatalog,
    staleTime: 5 * 60_000,
  })
}
