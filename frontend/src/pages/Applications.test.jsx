// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Applications from './Applications'
import { jobService } from '../services/api'
import { toLocalDateKey } from '../utils/applicationPipeline'

vi.mock('../services/api', () => ({
  jobService: {
    getApplications: vi.fn(),
    updateApplicationStatus: vi.fn(),
  },
}))

const baseApplication = {
  id: 'job-123',
  job_title: 'Platform Engineer',
  company: 'Example Co',
  location: 'Melbourne',
  application_status: 'saved',
  application_notes: 'Follow up after applying',
  next_action_at: null,
}

function renderApplications() {
  return render(
    <MemoryRouter>
      <Applications />
    </MemoryRouter>,
  )
}

function localDateOffset(days) {
  const date = new Date()
  date.setHours(12, 0, 0, 0)
  date.setDate(date.getDate() + days)
  return toLocalDateKey(date)
}

afterEach(cleanup)

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Applications', () => {
  it('shows loading, groups applications by status, and links cards to workspaces', async () => {
    let resolveApplications
    jobService.getApplications.mockReturnValue(new Promise((resolve) => {
      resolveApplications = resolve
    }))

    renderApplications()
    expect(screen.getByRole('status').textContent).toContain('Loading applications')

    resolveApplications([
      baseApplication,
      {
        ...baseApplication,
        id: 'job/456',
        job_title: 'Staff Engineer',
        application_status: 'interviewing',
      },
    ])

    expect(await screen.findByRole('heading', { name: 'Saved' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Interviewing' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Platform Engineer' }).getAttribute('href')).toBe('/applications/job-123')
    expect(screen.getByRole('link', { name: 'Staff Engineer' }).getAttribute('href')).toBe('/applications/job%2F456')
  })

  it('updates status inline and regroups the application', async () => {
    const user = userEvent.setup()
    jobService.getApplications.mockResolvedValue([baseApplication])
    jobService.updateApplicationStatus.mockResolvedValue({
      ...baseApplication,
      application_status: 'applied',
    })

    renderApplications()
    const status = await screen.findByLabelText('Status')
    await user.selectOptions(status, 'applied')

    await waitFor(() => {
      expect(jobService.updateApplicationStatus).toHaveBeenCalledWith(
        'job-123',
        'applied',
        'Follow up after applying',
        null,
      )
    })
    expect(await screen.findByRole('heading', { name: 'Applied' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Saved' })).toBeNull()
  })

  it('labels overdue, due-today, and upcoming follow-ups', async () => {
    jobService.getApplications.mockResolvedValue([
      { ...baseApplication, id: 'overdue', job_title: 'Overdue role', next_action_at: localDateOffset(-1) },
      { ...baseApplication, id: 'today', job_title: 'Today role', next_action_at: localDateOffset(0) },
      { ...baseApplication, id: 'upcoming', job_title: 'Upcoming role', next_action_at: localDateOffset(1) },
    ])

    renderApplications()

    expect(await screen.findByText(/^Overdue ·/)).toBeTruthy()
    expect(screen.getByText('Due today')).toBeTruthy()
    expect(screen.getByText(/^Upcoming ·/)).toBeTruthy()
  })

  it('shows load errors and offers a retry', async () => {
    jobService.getApplications.mockRejectedValue({ userMessage: 'Pipeline could not be loaded.' })

    renderApplications()

    expect(await screen.findByRole('heading', { name: 'Applications unavailable' })).toBeTruthy()
    expect(screen.getByRole('alert').textContent).toContain('Pipeline could not be loaded.')
    expect(screen.getByRole('button', { name: 'Try again' })).toBeTruthy()
  })

  it('rolls back an inline edit and shows its save error', async () => {
    jobService.getApplications.mockResolvedValue([baseApplication])
    jobService.updateApplicationStatus.mockRejectedValue({ userMessage: 'Update failed.' })

    renderApplications()
    const nextAction = await screen.findByLabelText('Next action')
    fireEvent.change(nextAction, { target: { value: '2026-08-01' } })

    expect((await screen.findByRole('alert')).textContent).toContain('Update failed.')
    expect(nextAction.value).toBe('')
  })
})
