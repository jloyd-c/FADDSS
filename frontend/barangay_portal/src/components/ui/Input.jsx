export default function Input({ label, error, hint, className = '', ...props }) {
  return (
    <div className={`space-y-1 ${className}`}>
      {label && (
        <label className="block text-sm font-medium text-gray-700">{label}</label>
      )}
      <input
        {...props}
        className={`w-full rounded-lg border px-3 py-2 text-sm transition-colors outline-none
          focus:ring-2 focus:ring-blue-500 focus:border-blue-500
          ${error
            ? 'border-red-400 bg-red-50 focus:ring-red-400 focus:border-red-400'
            : 'border-gray-300 bg-white hover:border-gray-400'
          }
          disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed`}
      />
      {error && <p className="text-xs text-red-600">{error}</p>}
      {hint && !error && <p className="text-xs text-gray-400">{hint}</p>}
    </div>
  )
}
