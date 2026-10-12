export type Side = 1 | 2

export interface GameEntry {
  set_number: number
  game_number: number
  p1_games: number
  p2_games: number
  winner: Side
  server: Side | null
  is_tiebreak: boolean
  points: string[] | null
}

export interface LiveSet {
  setNumber: number
  score: [number, number]
}

export interface SetView {
  setNumber: number
  games: GameEntry[]
  score: [number, number]
  live: boolean
}

export function buildSets(games: GameEntry[], liveSet: LiveSet | null): SetView[] {
  const bySet = new Map<number, GameEntry[]>()
  for (const game of games) {
    const list = bySet.get(game.set_number)
    if (list) list.push(game)
    else bySet.set(game.set_number, [game])
  }
  if (liveSet && !bySet.has(liveSet.setNumber)) bySet.set(liveSet.setNumber, [])

  return [...bySet]
    .sort(([a], [b]) => a - b)
    .map(([setNumber, setGames]) => {
      const live = setNumber === liveSet?.setNumber
      const last = setGames[setGames.length - 1]
      const score: [number, number] =
        live && liveSet ? liveSet.score : [last.p1_games, last.p2_games]
      return { setNumber, games: setGames, score, live }
    })
}

export function isMatchOver(setsWon: [number, number], nbSet: number): boolean {
  return Math.max(...setsWon) >= Math.max(1, nbSet)
}

export function isBreak(game: GameEntry): boolean {
  return !game.is_tiebreak && game.server !== null && game.server !== game.winner
}

export const POINT_TAGS: Record<string, string> = {
  BP: 'Break point',
  SP: 'Set point',
  MP: 'Match point',
}

export function splitPoint(entry: string): { score: string; tags: string[] } {
  const [score, ...tags] = entry.split(' ')
  return { score, tags }
}
