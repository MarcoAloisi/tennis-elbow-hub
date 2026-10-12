import { describe, expect, it } from 'vitest'
import { buildSets, isBreak, isMatchOver, splitPoint, type GameEntry } from './gameLog'

function row(set: number, game: number, p1: number, p2: number, extra: Partial<GameEntry> = {}): GameEntry {
  return {
    set_number: set,
    game_number: game,
    p1_games: p1,
    p2_games: p2,
    winner: 1,
    server: 1,
    is_tiebreak: false,
    points: null,
    ...extra,
  }
}

describe('buildSets', () => {
  it('takes the score of a finished set from its last row', () => {
    const rows = [row(1, 8, 5, 3), row(1, 9, 6, 3), row(2, 9, 5, 4), row(2, 10, 6, 4)]
    const sets = buildSets(rows, null)
    expect(sets.map((s) => [s.setNumber, s.score, s.live])).toEqual([
      [1, [6, 3], false],
      [2, [6, 4], false],
    ])
  })

  it('adds the in-progress set with its live score and no games', () => {
    const sets = buildSets([row(1, 9, 6, 3)], { setNumber: 2, score: [2, 1] })
    expect(sets.map((s) => [s.setNumber, s.score, s.live, s.games.length])).toEqual([
      [1, [6, 3], false, 1],
      [2, [2, 1], true, 0],
    ])
  })

  it('prefers the live score over the last row for the in-progress set', () => {
    const sets = buildSets([row(2, 3, 2, 1)], { setNumber: 2, score: [3, 1] })
    expect(sets).toHaveLength(1)
    expect(sets[0].score).toEqual([3, 1])
  })

  it('handles a match joined mid-way', () => {
    const sets = buildSets([row(2, 6, 4, 2)], null)
    expect(sets.map((s) => [s.setNumber, s.score])).toEqual([[2, [4, 2]]])
  })
})

describe('isBreak', () => {
  it('flags a game won by the receiver', () => {
    expect(isBreak(row(1, 1, 0, 1, { server: 1, winner: 2 }))).toBe(true)
  })

  it('does not flag a hold, a tiebreak, or an unknown server', () => {
    expect(isBreak(row(1, 1, 1, 0, { server: 1, winner: 1 }))).toBe(false)
    expect(isBreak(row(1, 13, 6, 7, { server: 1, winner: 2, is_tiebreak: true }))).toBe(false)
    expect(isBreak(row(1, 1, 0, 1, { server: null, winner: 2 }))).toBe(false)
  })
})

describe('isMatchOver', () => {
  it('treats nb_set 0 and 1 as best of 1', () => {
    expect(isMatchOver([0, 1], 1)).toBe(true)
    expect(isMatchOver([1, 0], 0)).toBe(true)
    expect(isMatchOver([0, 0], 1)).toBe(false)
  })

  it('needs 2 sets in best of 3 and 3 sets in best of 5', () => {
    expect(isMatchOver([1, 1], 2)).toBe(false)
    expect(isMatchOver([2, 0], 2)).toBe(true)
    expect(isMatchOver([2, 1], 3)).toBe(false)
    expect(isMatchOver([1, 3], 3)).toBe(true)
  })
})

describe('splitPoint', () => {
  it('leaves a plain point score without tags', () => {
    expect(splitPoint('15-0')).toEqual({ score: '15-0', tags: [] })
  })

  it('splits the break, set and match point tags off the score', () => {
    expect(splitPoint('30-40 BP')).toEqual({ score: '30-40', tags: ['BP'] })
    expect(splitPoint('40-0 MP')).toEqual({ score: '40-0', tags: ['MP'] })
    expect(splitPoint('30-40 SP BP')).toEqual({ score: '30-40', tags: ['SP', 'BP'] })
  })
})
