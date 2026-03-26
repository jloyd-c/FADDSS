export function formatDate(dateString) {
  if (!dateString) return '—'
  return new Intl.DateTimeFormat('en-PH', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(new Date(dateString))
}

export function formatDateTime(dateString) {
  if (!dateString) return '—'
  return new Intl.DateTimeFormat('en-PH', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(dateString))
}

export function formatPhoneNumber(number) {
  if (!number) return '—'
  return number.replace(/(\d{4})(\d{3})(\d{4})/, '$1-$2-$3')
}
