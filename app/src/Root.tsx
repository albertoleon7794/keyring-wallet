import { RootStack as KeyRingRootStack, useStore } from '@bifold/core'
import { BCState, Mode } from '@/store'
import BCSCRootStack from '@bcsc-theme/navigators/RootStack'

const Root: React.FC = () => {
  const [store] = useStore<BCState>()

  return store.mode === Mode.KeyRingSC ? <BCSCRootStack /> : <KeyRingRootStack />
}

export default Root
