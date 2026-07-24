import test from 'node:test'
import assert from 'node:assert/strict'
import {
  formatFitScore,
  getJobSource,
  getSafeExternalUrl,
  getWorkflowProgress,
} from './applicationWorkspace.js'

test('accepts only credential-free HTTP and HTTPS apply URLs', () => {
  assert.equal(getSafeExternalUrl('https://jobs.example.com/apply?id=42'), 'https://jobs.example.com/apply?id=42')
  assert.equal(getSafeExternalUrl('http://jobs.example.com/role'), 'http://jobs.example.com/role')
  assert.equal(getSafeExternalUrl('javascript:alert(1)'), null)
  assert.equal(getSafeExternalUrl('https://user:secret@jobs.example.com/apply'), null)
  assert.equal(getSafeExternalUrl('/relative/apply'), null)
  assert.equal(getSafeExternalUrl('not a URL'), null)
})

test('uses a validated hostname as the source label', () => {
  assert.equal(getJobSource('https://www.seek.com.au/job/123'), 'seek.com.au')
  assert.equal(getJobSource('javascript:alert(1)'), 'Source unavailable')
})

test('derives workflow progress from persisted job data', () => {
  assert.deepEqual(getWorkflowProgress({ application_status: 'saved' }), {
    analyse: true,
    tailor: false,
    apply: false,
    track: false,
  })
  assert.deepEqual(getWorkflowProgress({ application_status: 'saved', cv_link: '/cv.pdf' }), {
    analyse: true,
    tailor: true,
    apply: false,
    track: false,
  })
  assert.deepEqual(getWorkflowProgress({ application_status: 'interviewing' }), {
    analyse: true,
    tailor: true,
    apply: true,
    track: true,
  })
})

test('formats scores using their existing scale', () => {
  assert.equal(formatFitScore(8.4), '84%')
  assert.equal(formatFitScore(76, 100), '76%')
  assert.equal(formatFitScore(null), 'Unavailable')
})
