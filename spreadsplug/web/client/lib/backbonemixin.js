/* Taken from a very informative blogpost by Eldar Djafarov:
 * http://eldar.djafarov.com/2013/11/reactjs-mixing-with-backbone/
 */
(function() {
  'use strict';
  module.exports = {
    /* Forces an update when the underlying Backbone model instance has
     * changed. Users will have to implement getBackboneModels().
     * Also requires that React is loaded with addons.
     */
    __syncedModels: [],
    componentDidMount: function() {
      // Whenever there may be a change in the Backbone data, trigger a reconcile.
      this.getBackboneModels().forEach(this.injectModel, this);
    },
    componentWillUnmount: function() {
      // Ensure that we clean up any dangling references when the component is
      // destroyed.
      this.__syncedModels.forEach(function(model) {
        model.off(null, model.__updater, this);
      }, this);
    },
    injectModel: function(model){
      if(!~this.__syncedModels.indexOf(model)){
        var updater = function() {
          try {
            this.forceUpdate();
          } catch(e) {
            // This means the component is already being updated somewhere
            // else, so we just silently go on with our business.
            // This is most likely due to some AJAX callback that already
            // updated the model at the same time or slightly earlier.
          }
        }.bind(this, null);
        model.__updater = updater;
        model.on('add change remove', updater, this);
      }
    },
    bindTo: function(model, key){
      /* Allows for two-way databinding for Backbone models.
        * Use by passing it as a 'valueLink' property, e.g.:
        *   valueLink={this.bindTo(model, attribute)} */
      return {
        value: model.get(key),
        requestChange: function(value){
            model.set(key, value);
        }.bind(this)
      };
    }
  };
})();
