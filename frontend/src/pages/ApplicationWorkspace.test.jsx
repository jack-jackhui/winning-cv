// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ApplicationWorkspace from './ApplicationWorkspace'
import { jobService } from '../services/api'

vi.mock('../services/api', () => ({
  jobService: {
    getResult: vi.fn(),
    updateApplicationStatus: vi.fn(),
  },
}))

vi.mock('../services/telemetry', () => ({
  trackApplicationStatusUpdate: vi.fn(),
  trackJobDetailsOpen: vi.fn(),
}))

const baseJob = {
  id: 'recA1b2C3d4E5f6G7',
  job_title: 'Platform Engineer',
  company: 'Example Co',
  location: 'Melbourne',
  score: 8.7,
  score_breakdown: null,
  job_link: 'https://jobs.example.com/123',
  description: 'Build reliable systems',
  match_reasons: [],
  suggestions: [],
  cv_link: null,
  application_status: 'saved',
  application_notes: null,
}

function renderWorkspace() {
  return render(
    <MemoryRouter initialEntries={['/applications/recA1b2C3d4E5f6G7']}>
      <Routes>
        <Route path="/applications/:jobId" element={<ApplicationWorkspace />} />
      </Routes>
    </MemoryRouter>,
  )
}

afterEach(() => {
  cleanup()
})

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ApplicationWorkspace', () => {
  it('shows the not-found message for a 404', async () => {
    jobService.getResult.mockRejectedValue({ status: 404 })

    renderWorkspace()

    expect(await screen.findByRole('heading', { name: 'Application not found' })).toBeTruthy()
    expect(screen.getByText('This job is unavailable or is not in your matched jobs.')).toBeTruthy()
  })

  it('shows a generic load error', async () => {
    jobService.getResult.mockRejectedValue({ userMessage: 'The workspace could not be loaded.' })

    renderWorkspace()

    expect(await screen.findByRole('heading', { name: 'Workspace unavailable' })).toBeTruthy()
    expect(screen.getByRole('alert').textContent).toContain('The workspace could not be loaded.')
  })

  it('initializes tracking fields and applies the saved response', async () => {
    const user = userEvent.setup()
    jobService.getResult.mockResolvedValue({
      ...baseJob,
      application_status: 'interviewing',
      application_notes: 'Phone screen booked',
    })
    jobService.updateApplicationStatus.mockResolvedValue({
      ...baseJob,
      application_status: 'applied',
      application_notes: 'Submitted today',
    })

    renderWorkspace()

    const status = await screen.findByLabelText('Application status')
    const notes = screen.getByLabelText('Notes')
    expect(status.value).toBe('interviewing')
    expect(notes.value).toBe('Phone screen booked')

    fireEvent.change(status, { target: { value: 'applied' } })
    await user.clear(notes)
    await user.type(notes, 'Sent via company portal')
    await user.click(screen.getByRole('button', { name: 'Save tracking' }))

    await waitFor(() => {
      expect(jobService.updateApplicationStatus).toHaveBeenCalledWith(
        baseJob.id,
        'applied',
        'Sent via company portal',
      )
    })
    expect(await screen.findByText('Application tracking saved.')).toBeTruthy()
    expect(status.value).toBe('applied')
    expect(notes.value).toBe('Submitted today')
  })

  it('disables tracking controls after a 501 response', async () => {
    const user = userEvent.setup()
    jobService.getResult.mockResolvedValue(baseJob)
    jobService.updateApplicationStatus.mockRejectedValue({ status: 501 })

    renderWorkspace()

    const saveButton = await screen.findByRole('button', { name: 'Save tracking' })
    await user.click(saveButton)

    expect((await screen.findByRole('alert')).textContent).toContain('Application tracking is unavailable')
    expect(screen.getByText('Application tracking is unavailable for the configured storage backend.')).toBeTruthy()
    expect(screen.getByLabelText('Application status').disabled).toBe(true)
    expect(screen.getByLabelText('Notes').disabled).toBe(true)
    expect(saveButton.disabled).toBe(true)
  })
})
