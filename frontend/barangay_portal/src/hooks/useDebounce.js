import { useState, useEffect } from 'react'

/**
 * Returns a debounced version of `value` that only updates
 * after the user has stopped changing it for `delay` ms.
 *
 * Usage:
 *   const debouncedSearch = useDebounce(search, 350)
 *   useEffect(() => { fetchData(debouncedSearch) }, [debouncedSearch])
 */
export default function useDebounce(value, delay = 350) {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])

  return debounced
}
