import test from 'node:test'
import assert from 'node:assert/strict'
import {
  getFollowUpState,
  groupApplicationsByStatus,
  toLocalDateKey,
} from './applicationPipeline.js'

test('groups applications in existing status order and defaults unknown statuses to saved', () => {
  const groups = groupApplicationsByStatus([
    { id: '3', application_status: 'interviewing' },
    { id: '1', application_status: 'saved' },
    { id: '2', application_status: 'applied' },
    { id: '4', application_status: 'unexpected' },
  ])

  assert.deepEqual(groups.map(({ value }) => value), ['saved', 'applied', 'interviewing'])
  assert.deepEqual(groups[0].applications.map(({ id }) => id), ['1', '4'])
})

test('classifies follow-ups against local calendar dates', () => {
  const now = new Date(2026, 6, 27, 15, 30)

  assert.equal(getFollowUpState('2026-07-26', now).kind, 'overdue')
  assert.equal(getFollowUpState('2026-07-27', now).label, 'Due today')
  assert.equal(getFollowUpState('2026-07-28', now).kind, 'upcoming')
  assert.equal(getFollowUpState(null, now), null)
})

test('keeps HTML date values as local calendar keys', () => {
  assert.equal(toLocalDateKey('2026-07-27'), '2026-07-27')
  assert.equal(toLocalDateKey(new Date(2026, 6, 28, 1, 15)), '2026-07-28')
  assert.equal(toLocalDateKey('not-a-date'), '')
})
