import { BaseTourID, TourStep, contactOfferTourSteps, contactsTourSteps } from '@bifold/core'

import { credentialOfferTourSteps } from './CredentialOfferTourSteps'
import { credentialsTourSteps } from './CredentialsTourSteps'
import { homeTourSteps } from './HomeTourSteps'
import { proofRequestTourSteps } from './ProofRequestTourSteps'

// to extend, add " | KeyRingTourID" where KeyRingTourID has tour IDs specific to Key Ring
export type TourID = BaseTourID

type Tours = {
  [key in TourID]: TourStep[]
}

const tours: Tours = {
  homeTourSteps,
  credentialsTourSteps,
  credentialOfferTourSteps,
  contactOfferTourSteps,
  proofRequestTourSteps,
  contactsTourSteps,
}

export default tours
