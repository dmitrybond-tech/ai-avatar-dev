import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { SkillsList } from '../Skills';
import { getSkills } from '../../api/client';

vi.mock('../../api/client', () => ({
  getSkills: vi.fn(),
}));

const mockedGetSkills = vi.mocked(getSkills);

beforeEach(() => {
  mockedGetSkills.mockResolvedValue([
    { slug: 'communication', title: 'Communication', short: 'Clear messaging across teams.', tags: ['Soft', 'Team'] },
    { slug: 'analysis', title: 'Analysis', short: 'Look at the data and make decisions.', tags: [] },
  ]);
});

afterEach(() => {
  vi.clearAllMocks();
  cleanup();
});

describe('SkillsList', () => {
  it('renders fetched skills as cards with localized content', async () => {
    render(<SkillsList />);

    await waitFor(() => {
      expect(screen.getByText('Communication')).toBeInTheDocument();
    });

    expect(screen.getByText('Clear messaging across teams.')).toHaveClass('clamp-2');
    expect(screen.getAllByRole('button')).toHaveLength(2);

    const tagChip = screen.getByText('Soft');
    expect(tagChip).toBeInTheDocument();
    expect(tagChip).toHaveClass('rounded-full');

    expect(mockedGetSkills).toHaveBeenCalledTimes(1);
  });
});

