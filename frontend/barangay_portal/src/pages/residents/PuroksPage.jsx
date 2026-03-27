import { useState, useEffect, useCallback } from 'react'
import { MapPin, Plus, Pencil, Trash2 } from 'lucide-react'
import { getPuroks, createPurok, updatePurok, deletePurok } from '../../api/residentsApi'
import { Card, CardBody } from '../../components/ui/Card'
import Modal from '../../components/ui/Modal'
import Input from '../../components/ui/Input'
import Button from '../../components/ui/Button'
import { useToast } from '../../context/ToastContext'

const EMPTY_FORM = { number: '', name: '', description: '' }

export default function PuroksPage() {
  const [puroks,   setPuroks]   = useState([])
  const [loading,  setLoading]  = useState(true)
  const [saving,   setSaving]   = useState(false)
  const [deleting, setDeleting] = useState(null)

  // Modal state
  const [showModal,  setShowModal]  = useState(false)
  const [editTarget, setEditTarget] = useState(null)   // null = create, obj = edit
  const [form,       setForm]       = useState(EMPTY_FORM)
  const [errors,     setErrors]     = useState({})

  // Confirm delete
  const [confirmDelete, setConfirmDelete] = useState(null)

  const { showToast } = useToast()

  const load = useCallback(() => {
    setLoading(true)
    getPuroks({ page_size: 200 })
      .then(({ data: d }) => setPuroks(d.results ?? d))
      .catch(() => showToast('Failed to load puroks.', 'error'))
      .finally(() => setLoading(false))
  }, [showToast])

  useEffect(() => { load() }, [load])

  function openCreate() {
    setEditTarget(null)
    setForm(EMPTY_FORM)
    setErrors({})
    setShowModal(true)
  }

  function openEdit(purok) {
    setEditTarget(purok)
    setForm({ number: purok.number, name: purok.name ?? '', description: purok.description ?? '' })
    setErrors({})
    setShowModal(true)
  }

  async function handleSave() {
    const errs = {}
    if (!form.number) errs.number = 'Purok number is required.'
    else if (isNaN(Number(form.number)) || Number(form.number) < 1)
      errs.number = 'Must be a positive number.'
    if (Object.keys(errs).length) { setErrors(errs); return }

    setSaving(true)
    try {
      const payload = {
        number:      Number(form.number),
        name:        form.name.trim(),
        description: form.description.trim(),
      }
      if (editTarget) {
        await updatePurok(editTarget.id, payload)
        showToast('Purok updated.', 'success')
      } else {
        await createPurok(payload)
        showToast('Purok created.', 'success')
      }
      setShowModal(false)
      load()
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object') {
        setErrors(data)
      } else {
        showToast('Failed to save purok.', 'error')
      }
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(purok) {
    setDeleting(purok.id)
    try {
      await deletePurok(purok.id)
      showToast(`Purok ${purok.number} deleted.`, 'success')
      setConfirmDelete(null)
      load()
    } catch (err) {
      const detail = err.response?.data?.detail || 'Failed to delete purok.'
      showToast(detail, 'error')
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <MapPin size={22} className="text-blue-600" />
            Puroks
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Manage the barangay's purok divisions.
          </p>
        </div>
        <Button onClick={openCreate} className="gap-2">
          <Plus size={15} />
          Add Purok
        </Button>
      </div>

      {/* List */}
      <Card>
        <CardBody className="p-0">
          {loading ? (
            <p className="text-center text-sm text-gray-400 py-10">Loading…</p>
          ) : puroks.length === 0 ? (
            <div className="text-center py-12">
              <MapPin size={32} className="mx-auto text-gray-300 mb-3" />
              <p className="text-sm font-medium text-gray-500">No puroks yet</p>
              <p className="text-xs text-gray-400 mt-1">
                Click "Add Purok" to create the first one.
              </p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="text-left px-4 py-3 font-medium text-gray-600 w-20">No.</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600 hidden sm:table-cell">
                    Description
                  </th>
                  <th className="px-4 py-3 w-24" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {puroks.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50/60">
                    <td className="px-4 py-3 font-semibold text-gray-900">{p.number}</td>
                    <td className="px-4 py-3 text-gray-700">{p.name || <span className="text-gray-400 italic">—</span>}</td>
                    <td className="px-4 py-3 text-gray-500 hidden sm:table-cell truncate max-w-xs">
                      {p.description || <span className="text-gray-300 italic">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => openEdit(p)}
                          className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                          title="Edit"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => setConfirmDelete(p)}
                          className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardBody>
      </Card>

      {/* Create / Edit modal */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={editTarget ? `Edit Purok ${editTarget.number}` : 'Add New Purok'}
        size="sm"
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setShowModal(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : editTarget ? 'Save Changes' : 'Create Purok'}
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <Input
            label="Purok Number"
            type="number"
            min="1"
            value={form.number}
            onChange={(e) => setForm(f => ({ ...f, number: e.target.value }))}
            error={errors.number}
            required
          />
          <Input
            label="Name (optional)"
            value={form.name}
            onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
            placeholder="e.g. Sampaguita"
            error={errors.name}
          />
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <textarea
              rows={3}
              value={form.description}
              onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Brief description of this purok…"
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300
                focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none"
            />
            {errors.description && (
              <p className="text-xs text-red-500 mt-1">{errors.description}</p>
            )}
          </div>
        </div>
      </Modal>

      {/* Delete confirmation modal */}
      <Modal
        isOpen={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        title="Delete Purok"
        size="sm"
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setConfirmDelete(null)}>Cancel</Button>
            <Button
              variant="danger"
              onClick={() => handleDelete(confirmDelete)}
              disabled={deleting === confirmDelete?.id}
            >
              {deleting === confirmDelete?.id ? 'Deleting…' : 'Delete'}
            </Button>
          </div>
        }
      >
        <p className="text-sm text-gray-600">
          Are you sure you want to delete{' '}
          <span className="font-semibold text-gray-900">
            Purok {confirmDelete?.number}{confirmDelete?.name ? ` — ${confirmDelete.name}` : ''}
          </span>
          ? This cannot be undone and may affect households assigned to this purok.
        </p>
      </Modal>

    </div>
  )
}
