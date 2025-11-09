import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { SkillsPage } from '../SkillsPage'
import { getSkillDetail, getSkills } from '../../api/client'

vi.mock('../../api/client', () => ({
  getSkills: vi.fn(),
  getSkillDetail: vi.fn(),
}))

const mockedGetSkills = vi.mocked(getSkills)
const mockedGetSkillDetail = vi.mocked(getSkillDetail)

const baseSkills = [
  { slug: 'communication', title: 'Communication', short: 'Short text', tags: ['Soft'] },
  { slug: 'analysis', title: 'Analysis', short: 'Another short', tags: ['Data'] },
]

beforeEach(() => {
  mockedGetSkills.mockResolvedValue(baseSkills)
  mockedGetSkillDetail.mockResolvedValue({
    slug: 'communication',
    title: 'Communication',
    short: 'Short text',
    tags: ['Soft'],
    bullets: ['Listen actively', 'Clarify assumptions'],
    examples: ['Facilitated cross-team sync'],
  })
})

afterEach(() => {
  vi.clearAllMocks()
  cleanup()
})

describe('SkillsPage', () => {
  it('renders skills and opens detail modal by slug', async () => {
    const onSelect = vi.fn()
    const onCloseDetail = vi.fn()

    const { rerender } = render(
      <SkillsPage
        lang="en"
        selectedSlug={null}
        onBack={vi.fn()}
        onSelect={onSelect}
        onCloseDetail={onCloseDetail}
      />,
    )

    await waitFor(() => {
      expect(mockedGetSkills).toHaveBeenCalledWith('en', expect.anything())
      expect(screen.getByText('Communication')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Communication'))
    expect(onSelect).toHaveBeenCalledWith('communication')

    rerender(
      <SkillsPage
        lang="en"
        selectedSlug="communication"
        onBack={vi.fn()}
        onSelect={onSelect}
        onCloseDetail={onCloseDetail}
      />,
    )

    await waitFor(() => {
      expect(mockedGetSkillDetail).toHaveBeenCalledWith('communication', 'en', expect.anything())
    })

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toHaveTextContent('Listen actively')
    })
  })
})


