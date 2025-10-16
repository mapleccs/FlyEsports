export interface ParticipantNameContext {
  blueSideId?: string | number | null
  redSideId?: string | number | null
  blueSideName?: string | null
  redSideName?: string | null
}

const TEAM_NAME_MAP: Record<string, string> = {
  '5': '????',
  '8': '???',
  '6': '????',
  '7': '????',
  '9': '????',
  '10': '????',
}

/**
 * ????????????????????
 * ???????????????????????
 * ????? ID ????????????
 */
export function resolveParticipantDisplayName(
  participantId?: string | number,
  context?: ParticipantNameContext,
): string {
  if (!participantId) {
    return '???'
  }

  const idString = String(participantId)

  if (context) {
    if (
      context.blueSideId !== undefined &&
      context.blueSideId !== null &&
      String(context.blueSideId) === idString &&
      context.blueSideName
    ) {
      return context.blueSideName
    }

    if (
      context.redSideId !== undefined &&
      context.redSideId !== null &&
      String(context.redSideId) === idString &&
      context.redSideName
    ) {
      return context.redSideName
    }
  }

  const mappedName = TEAM_NAME_MAP[idString]
  if (mappedName) {
    return mappedName
  }

  if (idString.length >= 8) {
    return `?? ${idString.slice(0, 8)}`
  }

  return `??${idString}`
}
