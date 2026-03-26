export default function Select({ label, error, options = [], placeholder, className = '', ...props }) {
  return (
    <div className={`space-y-1 ${className}`}>
      {label && (
        <label className="block text-sm font-medium text-gray-700">{label}</label>
      )}
      <select
        {...props}
        className={`w-full rounded-lg border px-3 py-2 text-sm transition-colors outline-none bg-white
          focus:ring-2 focus:ring-blue-500 focus:border-blue-500
          ${error ? 'border-red-400' : 'border-gray-300 hover:border-gray-400'}
          disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed`}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map(({ value, label: optLabel }) => (
          <option key={value} value={value}>
            {optLabel}
          </option>
        ))}
      </select>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}
