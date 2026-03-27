/**
 * SchemaBuilderPage  — visual form-schema designer
 * ─────────────────────────────────────────────────────────────────────────────
 * Accessible only to SUPER_ADMIN and ADMIN.
 *
 * Features:
 *   • List all FormSchemas (by year / version)
 *   • Create new schema with drag-friendly section/field builder
 *   • Edit existing schema
 *   • Activate / deactivate a schema version
 *   • Per-field: id, label, type, required, help_text, options (for select)
 *
 * Schema JSON shape produced:
 *   { sections: [{ id, label, level, fields: [{ id, label, type, canonical,
 *                  required, help_text, cols, options }] }] }
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Settings2, Plus, Trash2, ChevronLeft, ChevronDown, ChevronUp,
  Save, Copy, ToggleLeft, ToggleRight, Eye, Pencil, AlertCircle,
  GripVertical, X, Check,
} from 'lucide-react'
import {
  getFormSchemas, getFormSchema,
  createFormSchema, updateFormSchema, deleteFormSchema,
} from '../../api/profilingApi'
import { useToast } from '../../context/ToastContext'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Modal from '../../components/ui/Modal'
import Badge from '../../components/ui/Badge'
import Spinner from '../../components/ui/Spinner'

// ── Constants ─────────────────────────────────────────────────────────────────

const FIELD_TYPES = [
  { value: 'text',        label: 'Text (single line)' },
  { value: 'textarea',    label: 'Text Area (multi-line)' },
  { value: 'number',      label: 'Number' },
  { value: 'date',        label: 'Date' },
  { value: 'boolean',     label: 'Yes / No (checkbox)' },
  { value: 'select',      label: 'Dropdown (single select)' },
  { value: 'multiselect', label: 'Multi-select (checkboxes)' },
  { value: 'radio',       label: 'Radio buttons' },
]

const SECTION_LEVELS = [
  { value: 'household', label: 'Household-level (fills HouseholdSurvey.data)' },
  { value: 'family',    label: 'Family-level (fills Family.data)' },
  { value: 'person',    label: 'Person-level (fills Person.data)' },
]

const TYPES_WITH_OPTIONS = new Set(['select', 'multiselect', 'radio'])

const EMPTY_FIELD = () => ({
  _fid:      crypto.randomUUID(),
  id:        '',
  label:     '',
  type:      'text',
  canonical: '',
  required:  false,
  help_text: '',
  cols:      1,
  options:   [],     // [{ value, label }]
})

const EMPTY_SECTION = () => ({
  _sid:   crypto.randomUUID(),
  id:     '',
  label:  '',
  level:  'household',
  fields: [],
})

const STATUS_COLORS = { true: 'green', false: 'gray' }

// ── Small helpers ─────────────────────────────────────────────────────────────

function slugify(str) {
  return str
    .toLowerCase()
    .replace(/[^a-z0-9\s_]/g, '')
    .trim()
    .replace(/\s+/g, '_')
}

// ── Option editor (for select / multiselect / radio) ─────────────────────────

function OptionEditor({ options, onChange }) {
  const add = () =>
    onChange([...options, { value: '', label: '' }])

  const upd = (i, key, val) =>
    onChange(options.map((o, idx) => idx === i ? { ...o, [key]: val } : o))

  const remove = (i) =>
    onChange(options.filter((_, idx) => idx !== i))

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-600">Answer Options</span>
        <button
          type="button"
          onClick={add}
          className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
        >
          <Plus size={11} /> Add option
        </button>
      </div>

      {options.length === 0 && (
        <p className="text-xs text-amber-600 italic">
          No options yet — add at least one.
        </p>
      )}

      <div className="space-y-1.5">
        {options.map((opt, i) => (
          <div key={i} className="flex items-center gap-2">
            <input
              type="text"
              value={opt.value}
              onChange={(e) => {
                const raw = e.target.value
                upd(i, 'value', raw.toUpperCase().replace(/\s+/g, '_'))
              }}
              placeholder="VALUE (e.g. METERED)"
              className="w-32 shrink-0 rounded-md border border-gray-300 px-2 py-1 text-xs
                focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none font-mono"
            />
            <input
              type="text"
              value={opt.label}
              onChange={(e) => upd(i, 'label', e.target.value)}
              placeholder="Display label"
              className="flex-1 rounded-md border border-gray-300 px-2 py-1 text-xs
                focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
            <button
              type="button"
              onClick={() => remove(i)}
              className="p-1 text-gray-400 hover:text-red-500 shrink-0"
            >
              <X size={12} />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Field editor card ─────────────────────────────────────────────────────────

function FieldCard({ field, index, total, onChange, onRemove, onMove }) {
  const [expanded, setExpanded] = useState(!field.id)

  const upd = (key, val) => onChange({ ...field, [key]: val })

  const handleLabelBlur = () => {
    if (!field.id && field.label) {
      upd('id', slugify(field.label))
    }
  }

  return (
    <div className="border border-gray-200 rounded-xl bg-white shadow-sm">

      {/* Header row */}
      <div className="flex items-center gap-2 px-3 py-2.5">
        <GripVertical size={14} className="text-gray-300 shrink-0 cursor-grab" />

        <div className="flex-1 min-w-0">
          {field.label
            ? <p className="text-sm font-medium text-gray-800 truncate">{field.label}</p>
            : <p className="text-sm text-gray-400 italic">Untitled field</p>
          }
          <p className="text-xs text-gray-400">
            {FIELD_TYPES.find(t => t.value === field.type)?.label ?? field.type}
            {field.id && <span className="font-mono ml-1.5 text-gray-300">#{field.id}</span>}
            {field.required && <span className="ml-1.5 text-red-400">required</span>}
          </p>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={() => onMove(index, -1)}
            disabled={index === 0}
            className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
            title="Move up"
          >
            <ChevronUp size={14} />
          </button>
          <button
            type="button"
            onClick={() => onMove(index, 1)}
            disabled={index === total - 1}
            className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
            title="Move down"
          >
            <ChevronDown size={14} />
          </button>
          <button
            type="button"
            onClick={() => setExpanded(e => !e)}
            className="p-1 text-gray-400 hover:text-blue-500"
          >
            {expanded ? <ChevronUp size={14} /> : <Pencil size={13} />}
          </button>
          <button
            type="button"
            onClick={onRemove}
            className="p-1 text-gray-400 hover:text-red-500"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {/* Expanded editor */}
      {expanded && (
        <div className="px-3 pb-3 pt-0 space-y-3 border-t border-gray-100">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3">

            <Input
              label="Label (display name) *"
              value={field.label}
              onChange={(e) => upd('label', e.target.value)}
              onBlur={handleLabelBlur}
              placeholder="e.g. Water Source"
            />

            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">
                Field ID *
                <span className="ml-1 text-xs font-normal text-gray-400">(key in data JSON)</span>
              </label>
              <input
                type="text"
                value={field.id}
                onChange={(e) => upd('id', slugify(e.target.value))}
                placeholder="e.g. water_source"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono
                  focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>

            <Select
              label="Field Type *"
              value={field.type}
              onChange={(e) => upd('type', e.target.value)}
              options={FIELD_TYPES}
            />

            <Input
              label="Canonical Name"
              value={field.canonical}
              onChange={(e) => upd('canonical', e.target.value)}
              placeholder="Links to FieldMapping (optional)"
            />

            <Input
              label="Help Text"
              value={field.help_text}
              onChange={(e) => upd('help_text', e.target.value)}
              placeholder="Hint shown below the field"
            />

            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">Width</label>
              <div className="flex gap-3">
                {[
                  { v: 1, label: 'Half (1 col)' },
                  { v: 2, label: 'Full (2 cols)' },
                ].map(({ v, label }) => (
                  <label key={v} className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="radio"
                      className="accent-blue-600"
                      checked={field.cols === v}
                      onChange={() => upd('cols', v)}
                    />
                    <span className="text-sm text-gray-700">{label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="sm:col-span-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="w-4 h-4 accent-blue-600 rounded"
                  checked={field.required}
                  onChange={(e) => upd('required', e.target.checked)}
                />
                <span className="text-sm font-medium text-gray-700">
                  Required field
                </span>
              </label>
            </div>
          </div>

          {/* Options — only for select/multiselect/radio */}
          {TYPES_WITH_OPTIONS.has(field.type) && (
            <div className="pt-2 border-t border-gray-100">
              <OptionEditor
                options={field.options ?? []}
                onChange={(opts) => upd('options', opts)}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Section editor ────────────────────────────────────────────────────────────

function SectionEditor({ section, index, total, onChange, onRemove, onMoveSection }) {
  const [collapsed, setCollapsed] = useState(false)

  const upd = (key, val) => onChange({ ...section, [key]: val })

  const addField = () =>
    upd('fields', [...section.fields, EMPTY_FIELD()])

  const updateField = (i, f) =>
    upd('fields', section.fields.map((x, idx) => idx === i ? f : x))

  const removeField = (i) =>
    upd('fields', section.fields.filter((_, idx) => idx !== i))

  const moveField = (i, dir) => {
    const arr  = [...section.fields]
    const swap = i + dir
    if (swap < 0 || swap >= arr.length) return
    ;[arr[i], arr[swap]] = [arr[swap], arr[i]]
    upd('fields', arr)
  }

  const handleLabelBlur = () => {
    if (!section.id && section.label) {
      upd('id', slugify(section.label))
    }
  }

  return (
    <div className="border-2 border-gray-200 rounded-2xl bg-gray-50">

      {/* Section header */}
      <div className="flex items-center gap-3 px-4 py-3">
        <GripVertical size={16} className="text-gray-300 shrink-0 cursor-grab" />

        <div className="flex-1 grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Input
            value={section.label}
            onChange={(e) => upd('label', e.target.value)}
            onBlur={handleLabelBlur}
            placeholder="Section name (e.g. Housing & Facilities)"
            className="sm:col-span-2"
          />
          <Select
            value={section.level}
            onChange={(e) => upd('level', e.target.value)}
            options={SECTION_LEVELS}
          />
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button type="button" onClick={() => onMoveSection(index, -1)} disabled={index === 0}
            className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30" title="Move up">
            <ChevronUp size={15} />
          </button>
          <button type="button" onClick={() => onMoveSection(index, 1)} disabled={index === total - 1}
            className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30" title="Move down">
            <ChevronDown size={15} />
          </button>
          <button type="button" onClick={() => setCollapsed(c => !c)}
            className="p-1 text-gray-500 hover:text-blue-600">
            {collapsed ? <ChevronDown size={15} /> : <ChevronUp size={15} />}
          </button>
          <button type="button" onClick={onRemove}
            className="p-1 text-gray-400 hover:text-red-500">
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Section body */}
      {!collapsed && (
        <div className="px-4 pb-4 space-y-2">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
              Fields
              <span className="ml-1.5 font-normal normal-case text-gray-400">
                ({section.fields.length})
              </span>
            </p>
            <button
              type="button"
              onClick={addField}
              className="flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-800"
            >
              <Plus size={12} /> Add field
            </button>
          </div>

          {section.fields.length === 0 && (
            <div className="flex flex-col items-center gap-1 py-6 border-2 border-dashed border-gray-200 rounded-xl text-gray-400">
              <Plus size={20} />
              <p className="text-xs">No fields yet. Click "Add field" to start.</p>
            </div>
          )}

          {section.fields.map((f, i) => (
            <FieldCard
              key={f._fid}
              field={f}
              index={i}
              total={section.fields.length}
              onChange={(upd) => updateField(i, upd)}
              onRemove={() => removeField(i)}
              onMove={moveField}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Schema metadata panel ─────────────────────────────────────────────────────

function SchemaMetaPanel({ meta, onChange }) {
  const upd = (key, val) => onChange({ ...meta, [key]: val })
  return (
    <Card>
      <CardHeader title="Schema Details" />
      <CardBody>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Input label="Schema Name *" value={meta.name}
            onChange={(e) => upd('name', e.target.value)}
            placeholder="e.g. Barangay Household Survey 2025"
            className="sm:col-span-2" />
          <Input label="Survey Year *" type="number" value={meta.year}
            onChange={(e) => upd('year', Number(e.target.value))}
            placeholder={String(new Date().getFullYear())} />
          <Input label="Version" type="number" value={meta.version}
            onChange={(e) => upd('version', Number(e.target.value))}
            placeholder="1" />
          <div className="sm:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea rows={2} value={meta.description}
              onChange={(e) => upd('description', e.target.value)}
              placeholder="Optional description of this survey form version"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm resize-none
                focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
          </div>
          <div className="flex items-center gap-2 pt-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" className="w-4 h-4 accent-blue-600 rounded"
                checked={meta.is_active}
                onChange={(e) => upd('is_active', e.target.checked)} />
              <span className="text-sm font-medium text-gray-700">
                Active (use for new surveys)
              </span>
            </label>
          </div>
        </div>
      </CardBody>
    </Card>
  )
}

// ── Schema Builder (editor view) ──────────────────────────────────────────────

function SchemaEditor({ schemaId, onSaved, onCancel }) {
  const toast = useToast()

  const [meta, setMeta] = useState({
    name: '', year: new Date().getFullYear(),
    version: 1, description: '', is_active: true,
  })
  const [sections, setSections] = useState([EMPTY_SECTION()])
  const [loading,  setLoading]  = useState(!!schemaId)
  const [saving,   setSaving]   = useState(false)
  const [preview,  setPreview]  = useState(false)

  // Load existing schema
  useEffect(() => {
    if (!schemaId) return
    setLoading(true)
    getFormSchema(schemaId)
      .then(({ data }) => {
        setMeta({
          name:        data.name,
          year:        data.year,
          version:     data.version,
          description: data.description ?? '',
          is_active:   data.is_active,
        })
        // Attach _sid / _fid for React keys
        const secs = (data.schema?.sections ?? []).map((s) => ({
          ...s,
          _sid:   crypto.randomUUID(),
          fields: (s.fields ?? []).map((f) => ({
            ...f,
            _fid:    crypto.randomUUID(),
            options: f.options ?? [],
            cols:    f.cols ?? 1,
          })),
        }))
        setSections(secs.length > 0 ? secs : [EMPTY_SECTION()])
      })
      .catch(() => toast('Failed to load schema', 'error'))
      .finally(() => setLoading(false))
  }, [schemaId, toast])

  const addSection = () =>
    setSections((s) => [...s, EMPTY_SECTION()])

  const updateSection = (i, sec) =>
    setSections((s) => s.map((x, idx) => idx === i ? sec : x))

  const removeSection = (i) =>
    setSections((s) => s.filter((_, idx) => idx !== i))

  const moveSection = (i, dir) => {
    const arr  = [...sections]
    const swap = i + dir
    if (swap < 0 || swap >= arr.length) return
    ;[arr[i], arr[swap]] = [arr[swap], arr[i]]
    setSections(arr)
  }

  const validate = () => {
    if (!meta.name.trim())  return 'Schema name is required.'
    if (!meta.year)         return 'Survey year is required.'
    if (sections.length === 0) return 'Add at least one section.'
    for (const sec of sections) {
      if (!sec.label.trim()) return 'All sections must have a name.'
      for (const f of sec.fields) {
        if (!f.id.trim())    return `A field in "${sec.label}" is missing a Field ID.`
        if (!f.label.trim()) return `A field in "${sec.label}" is missing a Label.`
        if (TYPES_WITH_OPTIONS.has(f.type) && f.options.length === 0)
          return `"${f.label}" needs at least one option.`
      }
    }
    return null
  }

  const handleSave = async () => {
    const err = validate()
    if (err) { toast(err, 'error'); return }

    setSaving(true)
    try {
      const payload = {
        ...meta,
        schema: {
          sections: sections.map(({ _sid, ...s }) => ({
            ...s,
            fields: s.fields.map(({ _fid, ...f }) => f),
          })),
        },
      }

      if (schemaId) {
        await updateFormSchema(schemaId, payload)
        toast('Schema updated successfully', 'success')
      } else {
        await createFormSchema(payload)
        toast('Schema created successfully', 'success')
      }
      onSaved()
    } catch (err) {
      const detail = err.response?.data?.detail
        ?? JSON.stringify(err.response?.data)
        ?? 'Failed to save schema'
      toast(detail, 'error')
    } finally {
      setSaving(false)
    }
  }

  const totalFields = sections.reduce((n, s) => n + s.fields.length, 0)

  if (loading) {
    return <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  }

  return (
    <div className="space-y-5">

      {/* Toolbar */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-lg font-bold text-gray-900">
            {schemaId ? 'Edit Schema' : 'New Form Schema'}
          </h2>
          <p className="text-sm text-gray-500">
            {sections.length} section(s) · {totalFields} field(s)
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={() => setPreview(true)} className="gap-2 text-sm">
            <Eye size={14} /> Preview JSON
          </Button>
          <Button variant="secondary" onClick={onCancel}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving} className="gap-2">
            <Save size={14} />
            {saving ? 'Saving…' : 'Save Schema'}
          </Button>
        </div>
      </div>

      {/* Meta */}
      <SchemaMetaPanel meta={meta} onChange={setMeta} />

      {/* Sections */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-gray-800">
            Sections & Fields
          </h3>
          <Button variant="ghost" onClick={addSection} className="gap-2 text-sm">
            <Plus size={14} /> Add Section
          </Button>
        </div>

        {sections.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-16 border-2 border-dashed border-gray-200 rounded-2xl text-gray-400">
            <Settings2 size={36} />
            <p className="text-sm">No sections yet. Add a section to start building your form.</p>
            <Button onClick={addSection} className="gap-2 mt-1">
              <Plus size={14} /> Add First Section
            </Button>
          </div>
        )}

        {sections.map((sec, i) => (
          <SectionEditor
            key={sec._sid}
            section={sec}
            index={i}
            total={sections.length}
            onChange={(upd) => updateSection(i, upd)}
            onRemove={() => removeSection(i)}
            onMoveSection={moveSection}
          />
        ))}
      </div>

      {sections.length > 0 && (
        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={saving} className="gap-2">
            <Save size={14} />
            {saving ? 'Saving…' : 'Save Schema'}
          </Button>
        </div>
      )}

      {/* JSON Preview modal */}
      <Modal
        isOpen={preview}
        onClose={() => setPreview(false)}
        title="Schema JSON Preview"
        size="xl"
        footer={<Button onClick={() => setPreview(false)}>Close</Button>}
      >
        <pre className="text-xs bg-gray-50 border border-gray-200 rounded-xl p-4 overflow-auto max-h-[60vh] whitespace-pre-wrap">
          {JSON.stringify(
            {
              sections: sections.map(({ _sid, ...s }) => ({
                ...s,
                fields: s.fields.map(({ _fid, ...f }) => f),
              })),
            },
            null, 2
          )}
        </pre>
      </Modal>
    </div>
  )
}

// ── Schema list card ──────────────────────────────────────────────────────────

function SchemaCard({ schema, onEdit, onToggle, onDelete }) {
  const totalFields = (schema.schema?.sections ?? [])
    .reduce((n, s) => n + (s.fields?.length ?? 0), 0)

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg shrink-0 ${schema.is_active ? 'bg-green-50' : 'bg-gray-100'}`}>
          <Settings2 size={18} className={schema.is_active ? 'text-green-600' : 'text-gray-400'} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-gray-900 truncate">{schema.name}</h3>
            <Badge color={STATUS_COLORS[schema.is_active]}>
              {schema.is_active ? 'Active' : 'Archived'}
            </Badge>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            Year {schema.year} · v{schema.version}
            {' · '}{(schema.schema?.sections ?? []).length} section(s)
            {' · '}{totalFields} field(s)
          </p>
          {schema.description && (
            <p className="text-xs text-gray-400 mt-1 line-clamp-1">{schema.description}</p>
          )}
        </div>
        <div className="flex gap-1 shrink-0">
          <button
            onClick={() => onToggle(schema)}
            className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition-colors"
            title={schema.is_active ? 'Deactivate' : 'Activate'}
          >
            {schema.is_active ? <ToggleRight size={16} /> : <ToggleLeft size={16} />}
          </button>
          <button
            onClick={() => onEdit(schema.id)}
            className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition-colors"
            title="Edit schema"
          >
            <Pencil size={14} />
          </button>
          <button
            onClick={() => onDelete(schema)}
            className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
            title="Delete schema"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function SchemaBuilderPage() {
  const navigate = useNavigate()
  const toast    = useToast()

  const [view,       setView]       = useState('list')   // 'list' | 'editor'
  const [editId,     setEditId]     = useState(null)
  const [schemas,    setSchemas]    = useState([])
  const [loading,    setLoading]    = useState(true)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting,   setDeleting]   = useState(false)

  const loadSchemas = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await getFormSchemas({ page_size: 100 })
      setSchemas(data.results ?? [])
    } catch {
      toast('Failed to load schemas', 'error')
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => { loadSchemas() }, [loadSchemas])

  const handleEdit = (id) => {
    setEditId(id)
    setView('editor')
  }

  const handleNew = () => {
    setEditId(null)
    setView('editor')
  }

  const handleSaved = () => {
    setView('list')
    loadSchemas()
  }

  const handleToggle = async (schema) => {
    try {
      await updateFormSchema(schema.id, { is_active: !schema.is_active })
      toast(
        schema.is_active ? 'Schema deactivated' : 'Schema activated',
        'success'
      )
      loadSchemas()
    } catch {
      toast('Failed to update schema status', 'error')
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteFormSchema(deleteTarget.id)
      toast('Schema deleted', 'success')
      setDeleteTarget(null)
      loadSchemas()
    } catch (err) {
      toast(err.response?.data?.detail ?? 'Failed to delete schema', 'error')
    } finally {
      setDeleting(false)
    }
  }

  // ── List view ──────────────────────────────────────────────────────────────

  if (view === 'editor') {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => setView('list')}
            className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronLeft size={18} />
          </button>
          <h1 className="text-xl font-bold text-gray-900">Schema Builder</h1>
        </div>
        <SchemaEditor
          schemaId={editId}
          onSaved={handleSaved}
          onCancel={() => setView('list')}
        />
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/profiling')}
            className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronLeft size={18} />
          </button>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-50 rounded-lg">
              <Settings2 size={20} className="text-indigo-600" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Schema Builder</h1>
              <p className="text-sm text-gray-500">
                Design the survey form fields for each year
              </p>
            </div>
          </div>
        </div>
        <Button onClick={handleNew} className="gap-2">
          <Plus size={15} />
          New Schema
        </Button>
      </div>

      {/* Info banner */}
      <div className="flex items-start gap-3 p-4 bg-indigo-50 border border-indigo-100 rounded-xl text-sm text-indigo-800">
        <AlertCircle size={15} className="shrink-0 mt-0.5" />
        <div>
          <p className="font-medium">What is a Form Schema?</p>
          <p className="mt-0.5 text-indigo-700">
            A schema defines what extra fields appear in the Survey Wizard beyond the fixed
            fields (household number, income bracket, name, gender, etc.).
            Create one schema per year. Only the <strong>Active</strong> schema is used for new surveys.
          </p>
        </div>
      </div>

      {/* Schema list */}
      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : schemas.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-20 text-gray-400">
          <Settings2 size={40} />
          <p className="text-sm">No schemas yet.</p>
          <Button onClick={handleNew} className="gap-2">
            <Plus size={14} /> Create First Schema
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {schemas.map((s) => (
            <SchemaCard
              key={s.id}
              schema={s}
              onEdit={handleEdit}
              onToggle={handleToggle}
              onDelete={setDeleteTarget}
            />
          ))}
        </div>
      )}

      {/* Delete confirm modal */}
      <Modal
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete Schema"
        size="sm"
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button variant="danger" onClick={handleDelete} disabled={deleting}>
              {deleting ? 'Deleting…' : 'Delete'}
            </Button>
          </div>
        }
      >
        <p className="text-sm text-gray-700">
          Are you sure you want to delete <strong>{deleteTarget?.name}</strong>?
          This cannot be undone. Existing surveys that used this schema will not be affected.
        </p>
      </Modal>
    </div>
  )
}
