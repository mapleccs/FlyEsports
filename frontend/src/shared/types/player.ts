/**
 * Player-related types
 */

export type Position = 'TOP' | 'JUNGLE' | 'MIDDLE' | 'BOTTOM' | 'UTILITY'

export type RankTier =
  | 'IRON'
  | 'BRONZE'
  | 'SILVER'
  | 'GOLD'
  | 'PLATINUM'
  | 'EMERALD'
  | 'DIAMOND'
  | 'MASTER'
  | 'GRANDMASTER'
  | 'CHALLENGER'

export type RankDivision = 'I' | 'II' | 'III' | 'IV'

export interface PlayerProfile {
  profile_id: string
  player_name: string
  summoner_name: string
  position: string
  current_rating: number
  effective_rating: number
  rank_display: string
  contract_status: string
  current_team_id?: string
  total_matches: number
  win_rate: number
  region_id: number
  created_at: string
  last_active?: string
}

export interface PlayerRegistrationData {
  region_id: number
  player_name: string
  summoner_name: string
  position: Position
  rank_tier?: RankTier
  rank_division?: RankDivision
  league_points?: number
  description?: string
}

export interface RegionSummary {
  region_id: number
  region_name: string
  status: string
  total_players: number
  active_players: number
  is_active: boolean
  created_at: string
}

// Constants
export const POSITIONS: { value: Position; label: string; description: string }[] = [
  { value: 'TOP', label: '上单', description: '上路单人线' },
  { value: 'JUNGLE', label: '打野', description: '野区游走支援' },
  { value: 'MIDDLE', label: '中单', description: '中路单人线' },
  { value: 'BOTTOM', label: '下路', description: '下路核心输出' },
  { value: 'UTILITY', label: '辅助', description: '下路辅助支援' },
]

export const RANK_TIERS: { value: RankTier; label: string; color: string }[] = [
  { value: 'IRON', label: '黑铁', color: '#8B4513' },
  { value: 'BRONZE', label: '青铜', color: '#CD7F32' },
  { value: 'SILVER', label: '白银', color: '#C0C0C0' },
  { value: 'GOLD', label: '黄金', color: '#FFD700' },
  { value: 'PLATINUM', label: '铂金', color: '#E5E4E2' },
  { value: 'EMERALD', label: '翡翠', color: '#50C878' },
  { value: 'DIAMOND', label: '钻石', color: '#B9F2FF' },
  { value: 'MASTER', label: '大师', color: '#9932CC' },
  { value: 'GRANDMASTER', label: '宗师', color: '#FF6B6B' },
  { value: 'CHALLENGER', label: '王者', color: '#F7E98E' },
]

export const RANK_DIVISIONS: { value: RankDivision; label: string }[] = [
  { value: 'I', label: 'I' },
  { value: 'II', label: 'II' },
  { value: 'III', label: 'III' },
  { value: 'IV', label: 'IV' },
]

// Helper functions
export function getRankTierInfo(tier: RankTier) {
  return RANK_TIERS.find(t => t.value === tier) || { value: tier, label: tier, color: '#666666' }
}

export function getPositionInfo(position: Position) {
  return (
    POSITIONS.find(p => p.value === position) || {
      value: position,
      label: position,
      description: '',
    }
  )
}
