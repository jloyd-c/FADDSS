/**
 * DynamicFormRenderer
 * ────────────────────────────────────────────────────────────────────────────
 * Renders a form driven by a FormSchema JSON payload from the API.
 *
 * Expects the parent to create a react-hook-form instance and pass
 * its helpers down:
 *
 *   const { register, control, formState: { errors }, watch, setValue } = useForm()
 *   <DynamicFormRenderer schema={schema} register={register} control={control}
 *                        errors={errors} watch={watch} setValue={setValue} />
 *
 * Schema field shape:
 *   { id, label, type, required?, choices?, hint?, placeholder?, cols? }
 *
 * Supported types:
 *   text · number · select · boolean · date · textarea · radio · multiselect
 */

import { Controller } from 'react-hook-form'

// ── Field components ──────────────────────────────────────────────────────────

function FieldWrapper({ label, hint, error, required, children }) {
  return (
    <div className="space-y-1">
      {label && (
        <label className="block text-sm font-medium text-gray-700">
          {label}
          {required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
      )}
      {children}
      {error  && <p className="text-xs text-red-600">{error.message || String(error)}</p>}
      {hint && !error && <p className="text-xs text-gray-400">{hint}</p>}
    </div>
  )
}

const baseInput =
  'w-full rounded-lg border px-3 py-2 text-sm transition-colors outline-none ' +
  'focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ' +
  'disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed '

const inputCls = (hasError) =>
  baseInput +
  (hasError
    ? 'border-red-400 bg-red-50 focus:ring-red-400'
    : 'border-gray-300 bg-white hover:border-gray-400')

// ── Text / Number / Date ──────────────────────────────────────────────────────

function TextField({ field, register, errors, readOnly }) {
  const typeMap = { text: 'text', number: 'number', date: 'date' }
  const err = errors[field.id]
  return (
    <FieldWrapper label={field.label} hint={field.hint} error={err} required={field.required}>
      <input
        type={typeMap[field.type] ?? 'text'}
        placeholder={field.placeholder ?? ''}
        disabled={readOnly}
        className={inputCls(!!err)}
        {...register(field.id, {
          required: field.required ? `${field.label} is required` : false,
          ...(field.type === 'number' && { valueAsNumber: true }),
        })}
      />
    </FieldWrapper>
  )
}

// ── Textarea ──────────────────────────────────────────────────────────────────

function TextareaField({ field, register, errors, readOnly }) {
  const err = errors[field.id]
  return (
    <FieldWrapper label={field.label} hint={field.hint} error={err} required={field.required}>
      <textarea
        rows={3}
        placeholder={field.placeholder ?? ''}
        disabled={readOnly}
        className={inputCls(!!err) + ' resize-none'}
        {...register(field.id, {
          required: field.required ? `${field.label} is required` : false,
        })}
      />
    </FieldWrapper>
  )
}

// ── Select ────────────────────────────────────────────────────────────────────

function SelectField({ field, register, errors, readOnly }) {
  const err = errors[field.id]
  const choices = field.choices ?? field.options ?? []
  return (
    <FieldWrapper label={field.label} hint={field.hint} error={err} required={field.required}>
      <select
        disabled={readOnly}
        className={inputCls(!!err)}
        {...register(field.id, {
          required: field.required ? `${field.label} is required` : false,
        })}
      >
        <option value="">— Select —</option>
        {choices.map((c) => {
          const val = typeof c === 'object' ? c.value : c
          const lbl = typeof c === 'object' ? c.label : c
          return (
            <option key={val} value={val}>
              {lbl}
            </option>
          )
        })}
      </select>
    </FieldWrapper>
  )
}

// ── Radio group ───────────────────────────────────────────────────────────────

function RadioField({ field, register, errors, readOnly }) {
  const err = errors[field.id]
  const choices = field.choices ?? field.options ?? []
  return (
    <FieldWrapper label={field.label} hint={field.hint} error={err} required={field.required}>
      <div className="flex flex-wrap gap-3 pt-1">
        {choices.map((c) => {
          const val = typeof c === 'object' ? c.value : c
          const lbl = typeof c === 'object' ? c.label : c
          return (
            <label key={val} className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="radio"
                value={val}
                disabled={readOnly}
                className="accent-blue-600"
                {...register(field.id, {
                  required: field.required ? `${field.label} is required` : false,
                })}
              />
              <span className="text-sm text-gray-700">{lbl}</span>
            </label>
          )
        })}
      </div>
    </FieldWrapper>
  )
}

// ── Boolean (single checkbox) ─────────────────────────────────────────────────

function BooleanField({ field, register, errors, readOnly }) {
  const err = errors[field.id]
  return (
    <FieldWrapper hint={field.hint} error={err}>
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          disabled={readOnly}
          className="w-4 h-4 accent-blue-600 rounded"
          {...register(field.id)}
        />
        <span className="text-sm font-medium text-gray-700">
          {field.label}
          {field.required && <span className="text-red-500 ml-0.5">*</span>}
        </span>
      </label>
    </FieldWrapper>
  )
}

// ── Multi-select (checkbox group) ─────────────────────────────────────────────

function MultiSelectField({ field, control, errors, readOnly }) {
  const err = errors[field.id]
  const choices = field.choices ?? field.options ?? []
  return (
    <FieldWrapper label={field.label} hint={field.hint} error={err} required={field.required}>
      <Controller
        name={field.id}
        control={control}
        defaultValue={[]}
        rules={{ required: field.required ? `${field.label} is required` : false }}
        render={({ field: { value, onChange } }) => (
          <div className="flex flex-wrap gap-x-4 gap-y-2 pt-1">
            {choices.map((c) => {
              const val = typeof c === 'object' ? c.value : c
              const lbl = typeof c === 'object' ? c.label : c
              const checked = Array.isArray(value) && value.includes(val)
              return (
                <label key={val} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    disabled={readOnly}
                    className="w-4 h-4 accent-blue-600 rounded"
                    checked={checked}
                    onChange={(e) => {
                      if (e.target.checked) {
                        onChange([...(value ?? []), val])
                      } else {
                        onChange((value ?? []).filter((v) => v !== val))
                      }
                    }}
                  />
                  <span className="text-sm text-gray-700">{lbl}</span>
                </label>
              )
            })}
          </div>
        )}
      />
    </FieldWrapper>
  )
}

// ── Field dispatcher ──────────────────────────────────────────────────────────

function DynamicField({ field, register, control, errors, readOnly }) {
  switch (field.type) {
    case 'text':
    case 'number':
    case 'date':
      return <TextField field={field} register={register} errors={errors} readOnly={readOnly} />
    case 'textarea':
      return <TextareaField field={field} register={register} errors={errors} readOnly={readOnly} />
    case 'select':
      return <SelectField field={field} register={register} errors={errors} readOnly={readOnly} />
    case 'radio':
      return <RadioField field={field} register={register} errors={errors} readOnly={readOnly} />
    case 'boolean':
    case 'checkbox':
      return <BooleanField field={field} register={register} errors={errors} readOnly={readOnly} />
    case 'multiselect':
      return <MultiSelectField field={field} control={control} errors={errors} readOnly={readOnly} />
    default:
      return <TextField field={field} register={register} errors={errors} readOnly={readOnly} />
  }
}

// ── Main export ───────────────────────────────────────────────────────────────

/**
 * Normalises both schema shapes into a list of { sectionLabel?, fields[] }.
 *
 * Shape A (sectioned — matches FormSchema.schema in the DB):
 *   { sections: [{ id, label, level, fields: [...] }] }
 *
 * Shape B (flat — used for simple one-off forms):
 *   { fields: [...] }
 */
function normaliseSections(schema) {
  if (!schema) return []
  if (Array.isArray(schema.sections) && schema.sections.length > 0) {
    return schema.sections.map((s) => ({
      id:     s.id,
      label:  s.label,
      level:  s.level,
      fields: s.fields ?? [],
    }))
  }
  // Flat schema — treat as a single anonymous section
  return [{ id: '_default', label: null, fields: schema.fields ?? [] }]
}

export default function DynamicFormRenderer({
  schema,
  register,
  control,
  errors = {},
  readOnly = false,
  /** Optional: only render fields belonging to this section level (household/family/person) */
  level = null,
}) {
  let sections = normaliseSections(schema)
  if (level) sections = sections.filter((s) => !s.level || s.level === level)

  const totalFields = sections.reduce((n, s) => n + s.fields.length, 0)

  if (totalFields === 0) {
    return (
      <p className="text-sm text-gray-400 italic py-2">
        No fields defined in this schema{level ? ` for level "${level}"` : ''}.
      </p>
    )
  }

  return (
    <div className="space-y-6">
      {sections.map((section) => (
        <div key={section.id}>
          {section.label && (
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
              {section.label}
            </p>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {section.fields.map((field) => (
              <div
                key={field.id}
                className={
                  field.cols === 2 || field.type === 'textarea' || field.type === 'multiselect'
                    ? 'sm:col-span-2'
                    : ''
                }
              >
                <DynamicField
                  field={field}
                  register={register}
                  control={control}
                  errors={errors}
                  readOnly={readOnly}
                />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
