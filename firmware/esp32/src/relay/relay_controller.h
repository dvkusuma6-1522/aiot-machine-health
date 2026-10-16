/**
 * @file relay_controller.h
 * @brief Optoisolated Relay Module Safety Controller
 */

#ifndef RELAY_CONTROLLER_H
#define RELAY_CONTROLLER_H

#include <stdint.h>
#include "config.h"

class RelayController {
public:
    RelayController();

    /**
     * @brief Initialize relay GPIO with safe default OFF state
     */
    void begin();

    /**
     * @brief Energize relay (drive LOW for active-LOW relay)
     */
    void relayOn();

    /**
     * @brief De-energize relay (drive HIGH for active-LOW relay - SAFE/OFF state)
     */
    void relayOff();

    /**
     * @brief Query current state of relay
     * @return true if relay is energized (motor enabled), false if de-energized (safe/off)
     */
    bool isRelayOn() const { return _isRelayOn; }

private:
    bool _isRelayOn;
};

#endif // RELAY_CONTROLLER_H
