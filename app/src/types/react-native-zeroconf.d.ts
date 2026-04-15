/**
 * Type declarations for react-native-zeroconf
 *
 * Basic TypeScript definitions for the react-native-zeroconf library
 * which provides mDNS/Zeroconf service discovery for React Native.
 */

declare module 'react-native-zeroconf' {
  /**
   * Service information returned by Zeroconf discovery
   */
  export interface ZeroconfService {
    /** Service name */
    name: string
    /** Service type */
    type?: string
    /** Service domain */
    domain?: string
    /** Hostname */
    host?: string
    /** IP addresses */
    addresses?: string[]
    /** Port number */
    port?: number
    /** TXT records */
    txt?: Record<string, string> | string[] | string
    /** Full name */
    fullName?: string
  }

  /**
   * Zeroconf event types
   */
  export type ZeroconfEvent =
    | 'start' // Scan started
    | 'stop' // Scan stopped
    | 'found' // Service found (but not yet resolved)
    | 'resolved' // Service fully resolved with details
    | 'remove' // Service removed/lost
    | 'error' // Error occurred
    | 'update' // Service updated

  /**
   * Zeroconf class for mDNS service discovery
   */
  export default class Zeroconf {
    /**
     * Create a new Zeroconf instance
     */
    constructor()

    /**
     * Start scanning for services
     * @param type - Service type (e.g., 'http', 'witness')
     * @param protocol - Protocol (e.g., 'tcp', 'udp')
     * @param domain - Domain (e.g., 'local.')
     */
    scan(type?: string, protocol?: string, domain?: string): void

    /**
     * Stop scanning for services
     */
    stop(): void

    /**
     * Add an event listener
     * @param event - Event name
     * @param callback - Callback function
     */
    on(event: 'error', callback: (error: Error) => void): void
    on(event: 'resolved' | 'remove' | 'found' | 'update', callback: (service: ZeroconfService) => void): void
    on(event: 'start' | 'stop', callback: () => void): void

    /**
     * Remove an event listener
     * @param event - Event name
     * @param callback - Callback function to remove
     */
    removeListener(event: 'error', callback: (error: Error) => void): void
    removeListener(
      event: 'resolved' | 'remove' | 'found' | 'update',
      callback: (service: ZeroconfService) => void
    ): void
    removeListener(event: 'start' | 'stop', callback: () => void): void

    /**
     * Remove all listeners for an event
     * @param event - Event name
     */
    removeAllListeners(event?: ZeroconfEvent): void

    /**
     * Get list of currently published services
     */
    getServices(): Record<string, ZeroconfService>

    /**
     * Publish a service (if supported by platform)
     * @param type - Service type
     * @param protocol - Protocol
     * @param domain - Domain
     * @param name - Service name
     * @param port - Port number
     * @param txt - TXT records
     */
    publishService(
      type: string,
      protocol: string,
      domain: string,
      name: string,
      port: number,
      txt?: Record<string, string>
    ): void

    /**
     * Unpublish a service
     * @param name - Service name to unpublish
     */
    unpublishService(name: string): void
  }
}
