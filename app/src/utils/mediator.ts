import { Agent, MediatorPickupStrategy } from '@credo-ts/core'

export const batchPickup = async (agent: Agent): Promise<void> => {
  try {
    for (let i = 0; i < 2; i++) {
      agent.config.logger.debug(`Batch pickup attempt ${i + 1}`)
      agent.mediationRecipient.initiateMessagePickup(undefined, MediatorPickupStrategy.Implicit)
      await new Promise((resolve) => setTimeout(resolve, 50))
    }
  } catch (error) {
    agent.config.logger.error(`Error during batch pickup: ${error}`)
  }
}

export const startPeriodicTrustPing = (agent: Agent, intervalMs: number): (() => void) => {
  const id = setInterval(async () => {
    try {
      const mediator = await agent.mediationRecipient.findDefaultMediator()
      if (!mediator) return

      await agent.connections.sendPing(mediator.connectionId, {
        responseRequested: false,
        withReturnRouting: true,
      })
    } catch (error) {
      agent.config.logger.error(`Periodic trust ping failed: ${error}`)
    }
  }, intervalMs)

  return () => clearInterval(id)
}
