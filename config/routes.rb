Rails.application.routes.draw do
  # Define your application routes per the DSL in https://guides.rubyonrails.org/routing.html

  # Reveal health status on /up that returns 200 if the app boots with no exceptions, otherwise 500.
  # Can be used by load balancers and uptime monitors to verify that the app is live.
  get "up" => "rails/health#show", as: :rails_health_check

  # 開発用のダミーのOpenAI API互換エンドポイント
  namespace :v1 do
    post "chat/completions", to: "chat#completions"
  end

  # Render dynamic PWA files from app/views/pwa/* (remember to link manifest in application.html.erb)
  # get "manifest" => "rails/pwa#manifest", as: :pwa_manifest
  # get "service-worker" => "rails/pwa#service_worker", as: :pwa_service_worker

  # Defines the root path route ("/")
  root "home#index"

  namespace :attack do
    resources :reports, only: [ :index, :show, :create, :destroy ] do
      collection do
        get :uncompleted
      end
    end
    resources :scenarios do
      collection do
        get "import/new", to: "scenarios#new_import", as: :new_import
        post "import", to: "scenarios#create_import", as: :import
      end
      new do
        patch "form", to: "scenarios#ensure_blank_fields_for_new_scenario", as: :form
      end
      member do
        patch "form", to: "scenarios#ensure_blank_fields_for_scenario", as: :form
        get "download"
      end
      resources :prompt_sets, only: [ :create ]
    end

    resources :prompt_sets, only: [ :index, :show, :destroy ] do
      collection do
        get :uncompleted
      end
      member do
        get :download
      end
    end
  end

  namespace :defense do
    resources :initial_policies, only: [ :index, :show, :new, :create, :edit, :update, :destroy ]
    resources :policies, only: [ :index, :show, :destroy ]
    resources :extensions, only: [ :index, :create, :destroy ] do
      collection do
        get :uncompleted
      end
    end
    resources :training_datasets, only: [ :index, :show, :create, :destroy ] do
      collection do
        get :uncompleted
      end
      member do
        get :download
      end
    end
  end

  # ホットモック用のルーティング
  get "attack_scenarios" => "home#attack_scenarios_index"
  get "attack_scenarios/1" => "home#attack_scenarios_show"

  get "attack_prompt_collections" => "home#attack_prompt_collections_index"
  get "attack_prompt_collections/1" => "home#attack_prompt_collections_show"

  get "attacks" => "home#attacks_index"
  get "attacks/1" => "home#attacks_show"

  # ダミージョブエンドポイント
  get "jobs/dummy/1" => "home#dummy_job"
  get "jobs/dummy_python/new" => "home#dummy_python_job_new"
  get "jobs/progress" => "home#job_progress"

  get "tbd" => "home#tbd"

  mount ActionCable.server => "/cable"
end
