<template>
  <div class="flex h-[calc(100vh-3.5rem)] bg-gray-950 text-gray-100 font-sans">
    <!-- Not Logged In View -->
    <div v-if="!isLoggedIn" class="w-full flex items-center justify-center">
      <div class="text-center space-y-6">
        <h1 class="text-5xl font-bold text-gray-100">Document Center</h1>
        <p class="text-xl text-gray-400 py-4">
          A collaborative platform for managing and sharing documents
        </p>
        <div class="pt-8">
          <router-link
            to="/login"
            class="px-6 py-3 bg-cyan-700 text-white rounded-lg hover:bg-cyan-600 transition-colors duration-300"
          >
            Get Started
          </router-link>
        </div>
      </div>
    </div>

    <!-- Logged In View -->
    <div v-else class="w-full p-6 overflow-auto">
      <div class="max-w-6xl mx-auto">
        <div
          v-if="isLoggedIn"
          class="max-w-6xl mx-auto mb-4 flex justify-end gap-3"
        >
          <button
            v-if="isGlobalAdmin"
            @click="showAddUserModal = true"
            class="px-3 py-1.5 bg-cyan-800 text-white rounded-lg hover:bg-cyan-700 transition-colors duration-300 flex items-center gap-2 text-sm"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                d="M8 9a3 3 0 100-6 3 3 0 000 6zM8 11a6 6 0 016 6H2a6 6 0 016-6z"
              />
              <path
                d="M16 7a1 1 0 10-2 0v1h-1a1 1 0 100 2h1v1a1 1 0 102 0v-1h1a1 1 0 100-2h-1V7z"
              />
            </svg>
            Add User
          </button>
          <button
            v-if="isGlobalAdmin"
            @click="showAddGroupModal = true"
            class="px-3 py-1.5 bg-cyan-800 text-white rounded-lg hover:bg-cyan-700 transition-colors duration-300 flex items-center gap-2 text-sm"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z"
              />
            </svg>
            Add Group
          </button>
          <button
            v-if="hasAnyGroupAdminRole"
            @click="showAssignRoleModal = true"
            class="px-3 py-1.5 bg-cyan-800 text-white rounded-lg hover:bg-cyan-700 transition-colors duration-300 flex items-center gap-2 text-sm"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
                clip-rule="evenodd"
              />
            </svg>
            Assign Role
          </button>
        </div>

        <!-- Add search and filter section -->
        <div class="mb-8 space-y-4 pt-2">
          <!-- Search bar -->
          <div class="relative">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search documents..."
              class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none pl-10"
            />
            <svg
              class="absolute left-3 top-2.5 h-5 w-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>

          <!-- Status filters -->
          <div class="flex flex-wrap gap-2">
            <button
              v-for="status in statusFilters"
              :key="status.value"
              @click="toggleStatusFilter(status.value)"
              :class="[
                'px-3 py-1.5 rounded-2xl text-sm transition-colors duration-200',
                selectedStatuses.includes(status.value)
                  ? status.activeClass
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700',
              ]"
            >
              {{ status.label }}
            </button>
          </div>
        </div>

        <div class="flex justify-between items-center mb-8">
          <h2 class="text-2xl font-bold text-gray-100">Documents</h2>
          <button
            @click="showCreateModal = true"
            class="px-4 py-2 bg-cyan-700 text-white rounded-lg hover:bg-cyan-600 transition-colors duration-300 flex items-center gap-2"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                clip-rule="evenodd"
              />
            </svg>
            New Document
          </button>
        </div>

        <!-- Documents Grid with Enhanced Animation -->
        <transition-group
          name="staggered-fade"
          tag="div"
          class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4"
          @before-enter="beforeEnter"
          @enter="enter"
          @leave="leave"
        >
          <div
            v-for="(doc, index) in filteredDocuments"
            :key="doc.id"
            :data-index="index"
            class="flex flex-col bg-gray-800 rounded-lg overflow-hidden border border-gray-700"
          >
            <div class="p-6 flex-grow">
              <div class="flex justify-between items-start mb-4">
                <h3 class="text-lg font-semibold text-gray-100 truncate mr-4">
                  {{ doc.title }}
                </h3>
                <span
                  :class="getStatusClass(doc.status)"
                  class="px-2 py-1 rounded-full text-xs whitespace-nowrap"
                >
                  {{ mapStatus(doc.status) }}
                </span>
              </div>

              <p
                class="text-gray-400 text-sm mb-4 line-clamp-2 h-[2.5rem] overflow-hidden"
              >
                {{ doc.description }}
              </p>

              <div class="flex items-center text-xs text-gray-400 gap-2 mt-2">
                <span class="text-cyan-500">{{
                  usernames[doc.creatorId] || doc.creatorId
                }}</span>
                <span>•</span>
                <span>Last updated {{ formatDate(doc.updatedAt) }}</span>
              </div>
            </div>

            <div
              class="p-3 border-t border-gray-700 bg-gray-800/50 flex items-center"
            >
              <div class="flex justify-between w-full">
                <!-- Admin button on left -->
                <div>
                  <button
                    v-if="isAdmin(doc.realmId)"
                    @click="adminAction(doc.id)"
                    class="text-xs px-3 py-1.5 bg-gray-800 text-white rounded hover:bg-gray-700 transition-colors duration-200"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                      />
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                      />
                    </svg>
                  </button>
                </div>

                <!-- Other action buttons on right -->
                <div class="flex gap-3">
                  <!-- Draft actions -->
                  <template v-if="doc.status === 'draft'">
                    <button
                      @click="editDocument(doc.id)"
                      class="text-xs px-3 py-1.5 border border-cyan-700 text-cyan-700 rounded hover:bg-cyan-700 hover:text-white transition-colors duration-200"
                    >
                      Edit
                    </button>
                    <button
                      @click="submitForReview(doc.id)"
                      class="text-xs px-3 py-1.5 bg-cyan-700 text-white rounded hover:bg-cyan-600 transition-colors duration-200"
                    >
                      Submit for Review
                    </button>
                  </template>

                  <!-- Pending Review actions -->
                  <template v-if="doc.status === 'pending_review'">
                    <button
                      @click="viewDocument(doc.id)"
                      class="text-xs px-3 py-1.5 border border-cyan-700 text-cyan-700 rounded hover:bg-cyan-700 hover:text-white transition-colors duration-200"
                    >
                      View
                    </button>
                    <button
                      v-if="doc.currentReviewerId === getCurrentUserId()"
                      @click="reviewDocument(doc.id)"
                      class="text-xs px-3 py-1.5 bg-cyan-700 text-white rounded hover:bg-cyan-600 transition-colors duration-200"
                    >
                      Review
                    </button>
                  </template>

                  <!-- Published actions -->
                  <template v-if="doc.status === 'published'">
                    <button
                      @click="viewDocument(doc.id)"
                      class="text-xs px-3 py-1.5 border border-cyan-700 text-cyan-700 rounded hover:bg-cyan-700 hover:text-white transition-colors duration-200"
                    >
                      View
                    </button>
                  </template>

                  <!-- Rejected actions -->
                  <template v-if="doc.status === 'rejected'">
                    <button
                      @click="editDocument(doc.id)"
                      class="text-xs px-3 py-1.5 border border-cyan-700 text-cyan-700 rounded hover:bg-cyan-700 hover:text-white transition-colors duration-200"
                    >
                      Edit
                    </button>
                    <button
                      @click="submitForReview(doc.id)"
                      class="text-xs px-3 py-1.5 bg-cyan-700 text-white rounded hover:bg-cyan-600 transition-colors duration-200"
                    >
                      Submit for Review
                    </button>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </transition-group>

        <!-- Create Document Modal -->
        <Transition
          enter-active-class="transition duration-300 ease-out"
          enter-from-class="transform opacity-0"
          enter-to-class="transform opacity-100"
          leave-active-class="transition duration-200 ease-in"
          leave-from-class="transform opacity-100"
          leave-to-class="transform opacity-0"
        >
          <div
            v-if="showCreateModal"
            class="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div
              class="fixed inset-0 bg-gray-950/90 backdrop-blur-sm"
              @click="showCreateModal = false"
            ></div>
            <div
              class="bg-gray-800 rounded-lg p-6 w-full max-w-md relative z-10"
            >
              <h3 class="text-xl font-semibold mb-4">Create New Document</h3>
              <form @submit.prevent="createDocument">
                <div class="mb-4">
                  <label class="block text-sm font-medium mb-2">Title</label>
                  <input
                    v-model="newDocument.title"
                    type="text"
                    class="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
                    required
                  />
                </div>
                <div class="mb-4">
                  <label class="block text-sm font-medium mb-2"
                    >Description</label
                  >
                  <textarea
                    v-model="newDocument.description"
                    class="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
                    rows="3"
                  ></textarea>
                </div>
                <div class="mb-6">
                  <label class="block text-sm font-medium mb-2">Group</label>
                  <select
                    v-model="newDocument.realmId"
                    class="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
                    required
                  >
                    <option value="" disabled>Select a group</option>
                    <option
                      v-for="group in userGroups"
                      :key="group.id"
                      :value="group.id"
                    >
                      {{ group.name }}
                    </option>
                  </select>
                </div>
                <div class="flex justify-end gap-3">
                  <button
                    type="button"
                    @click="showCreateModal = false"
                    class="px-4 py-2 text-gray-300 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    class="px-4 py-2 bg-cyan-700 text-white rounded-lg hover:bg-cyan-600"
                  >
                    Create
                  </button>
                </div>
              </form>
            </div>
          </div>
        </Transition>

        <!-- Add User Modal -->
        <Transition
          enter-active-class="transition duration-300 ease-out"
          enter-from-class="transform opacity-0"
          enter-to-class="transform opacity-100"
          leave-active-class="transition duration-200 ease-in"
          leave-from-class="transform opacity-100"
          leave-to-class="transform opacity-0"
        >
          <div
            v-if="showAddUserModal"
            class="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div
              class="fixed inset-0 bg-gray-950/90 backdrop-blur-sm"
              @click="showAddUserModal = false"
            ></div>
            <div
              class="bg-gray-800 rounded-lg p-6 w-full max-w-md relative z-10"
            >
              <h3 class="text-xl font-semibold mb-4">Add New User</h3>
              <form @submit.prevent="createUser">
                <div class="mb-4">
                  <label class="block text-sm font-medium mb-2">Username</label>
                  <input
                    v-model="newUser.username"
                    type="text"
                    class="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
                    required
                  />
                </div>
                <div class="mb-4">
                  <label class="block text-sm font-medium mb-2">Password</label>
                  <input
                    v-model="newUser.password"
                    type="password"
                    class="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
                    required
                  />
                </div>
                <div class="mb-6">
                  <label class="block text-sm font-medium mb-2">Role</label>
                  <select
                    v-model="newUser.global_role"
                    class="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
                    required
                  >
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <div class="flex justify-end gap-3">
                  <button
                    type="button"
                    @click="showAddUserModal = false"
                    class="px-4 py-2 text-gray-300 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    class="px-4 py-2 bg-cyan-700 text-white rounded-lg hover:bg-cyan-600"
                  >
                    Create User
                  </button>
                </div>
              </form>
            </div>
          </div>
        </Transition>

        <!-- Assign Role Modal -->
        <Transition
          enter-active-class="transition duration-300 ease-out"
          enter-from-class="transform opacity-0"
          enter-to-class="transform opacity-100"
          leave-active-class="transition duration-200 ease-in"
          leave-from-class="transform opacity-100"
          leave-to-class="transform opacity-0"
        >
          <div
            v-if="showAssignRoleModal"
            class="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div
              class="fixed inset-0 bg-gray-950/90 backdrop-blur-sm"
              @click="showAssignRoleModal = false"
            ></div>
            <div
              class="bg-gray-800 rounded-lg p-6 w-full max-w-md relative z-10"
            >
              <h3 class="text-xl font-semibold mb-4">Assign User Role</h3>
              <form @submit.prevent="assignUserRole">
                <div class="mb-4">
                  <label class="block text-sm font-medium mb-2">Group</label>
                  <select
                    v-model="roleAssignment.group_name"
                    class="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
                    required
                    @change="selectedGroupChanged"
                  >
                    <option value="" disabled>Select a group</option>
                    <option
                      v-for="group in adminGroups"
                      :key="group.id"
                      :value="group.name"
                    >
                      {{ group.name }}
                    </option>
                  </select>
                </div>
                <div class="mb-4">
                  <label class="block text-sm font-medium mb-2">User</label>
                  <select
                    v-model="roleAssignment.username"
                    class="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
                    required
                  >
                    <option value="" disabled>Select a user</option>
                    <option
                      v-for="user in allUsers"
                      :key="user.id"
                      :value="user.username"
                    >
                      {{ user.username }}
                    </option>
                  </select>
                </div>
                <div class="mb-6">
                  <label class="block text-sm font-medium mb-2">Role</label>
                  <div class="space-y-2">
                    <div class="flex items-center">
                      <input
                        type="checkbox"
                        id="role-user"
                        value="user"
                        v-model="roleAssignment.roles"
                        class="mr-2 bg-gray-700 rounded text-cyan-500 focus:ring-cyan-500"
                      />
                      <label for="role-admin" class="text-sm">User</label>
                    </div>
                    <div class="flex items-center">
                      <input
                        type="checkbox"
                        id="role-reviewer"
                        value="reviewer"
                        v-model="roleAssignment.roles"
                        class="mr-2 bg-gray-700 rounded text-cyan-500 focus:ring-cyan-500"
                      />
                      <label for="role-reviewer" class="text-sm"
                        >Reviewer</label
                      >
                    </div>
                    <div class="flex items-center">
                      <input
                        type="checkbox"
                        id="role-admin"
                        value="admin"
                        v-model="roleAssignment.roles"
                        class="mr-2 bg-gray-700 rounded text-cyan-500 focus:ring-cyan-500"
                      />
                      <label for="role-admin" class="text-sm">Admin</label>
                    </div>
                  </div>
                </div>
                <div class="flex justify-end gap-3">
                  <button
                    type="button"
                    @click="showAssignRoleModal = false"
                    class="px-4 py-2 text-gray-300 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    class="px-4 py-2 bg-cyan-700 text-white rounded-lg hover:bg-cyan-600"
                  >
                    Assign Role
                  </button>
                </div>
              </form>
            </div>
          </div>
        </Transition>

        <!-- Add Group Modal -->
        <Transition
          enter-active-class="transition duration-300 ease-out"
          enter-from-class="transform opacity-0"
          enter-to-class="transform opacity-100"
          leave-active-class="transition duration-200 ease-in"
          leave-from-class="transform opacity-100"
          leave-to-class="transform opacity-0"
        >
          <div
            v-if="showAddGroupModal"
            class="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div
              class="fixed inset-0 bg-gray-950/90 backdrop-blur-sm"
              @click="showAddGroupModal = false"
            ></div>
            <div
              class="bg-gray-800 rounded-lg p-6 w-full max-w-md relative z-10"
            >
              <h3 class="text-xl font-semibold mb-4">Create New Group</h3>
              <form @submit.prevent="createGroup">
                <div class="mb-4">
                  <label class="block text-sm font-medium mb-2"
                    >Group Name</label
                  >
                  <input
                    v-model="newGroup.group_name"
                    type="text"
                    class="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:ring-2 focus:ring-cyan-500 outline-none"
                    required
                  />
                </div>
                <div class="flex justify-end gap-3 mt-6">
                  <button
                    type="button"
                    @click="showAddGroupModal = false"
                    class="px-4 py-2 text-gray-300 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    class="px-4 py-2 bg-cyan-700 text-white rounded-lg hover:bg-cyan-600"
                  >
                    Create Group
                  </button>
                </div>
              </form>
            </div>
          </div>
        </Transition>

        <!-- Submit For Review Modal -->
        <SubmitForReviewModal
          :show="showSubmitModal"
          :document-id="selectedDocumentId"
          :group-id="selectedGroupId"
          @close="showSubmitModal = false"
          @submitted="handleReviewSubmitted"
        />
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import {
  documentService,
  authService,
  notificationService,
} from "../services/api";
import { authStore } from "../store/auth";
import SubmitForReviewModal from "../components/SubmitForReviewModal.vue";

export default {
  name: "Home",
  components: {
    SubmitForReviewModal,
  },
  setup() {
    const router = useRouter();
    const route = useRoute();
    const documents = ref([]);
    const isLoggedIn = computed(() => authStore.token);
    const isReviewer = ref(true);
    const showCreateModal = ref(false);
    const showSubmitModal = ref(false);
    const showAddUserModal = ref(false);
    const showAssignRoleModal = ref(false);
    const showAddGroupModal = ref(false);
    const selectedDocumentId = ref(null);
    const selectedGroupId = ref(null);
    const userGroups = ref([]);
    const newDocument = ref({
      title: "",
      description: "",
      realmId: "",
    });
    const newUser = ref({
      username: "",
      password: "",
      global_role: "user",
    });
    const newGroup = ref({
      group_name: "",
    });
    const roleAssignment = ref({
      group_name: "",
      username: "",
      roles: [],
    });
    const groupNames = ref({});
    const usernames = ref({});
    const searchQuery = ref("");
    const selectedStatuses = ref([]);
    const allUsers = ref([]);
    const adminGroups = ref([]);

    const statusFilters = [
      { label: "All", value: "", activeClass: "bg-cyan-700 text-white" },
      { label: "Draft", value: "draft", activeClass: "bg-gray-600 text-white" },
      {
        label: "Pending Review",
        value: "pending_review",
        activeClass: "bg-yellow-600 text-white",
      },
      {
        label: "Published",
        value: "published",
        activeClass: "bg-green-600 text-white",
      },
      {
        label: "Rejected",
        value: "rejected",
        activeClass: "bg-red-600 text-white",
      },
    ];

    const toggleStatusFilter = (status) => {
      if (status === "") {
        // If "All" is clicked, clear other filters
        selectedStatuses.value = [];
        return;
      }

      const index = selectedStatuses.value.indexOf(status);
      if (index === -1) {
        selectedStatuses.value.push(status);
      } else {
        selectedStatuses.value.splice(index, 1);
      }
    };

    const filteredDocuments = computed(() => {
      return documents.value
        .filter((doc) => {
          // Apply search filter
          const searchLower = searchQuery.value.toLowerCase();
          const matchesSearch =
            doc.title.toLowerCase().includes(searchLower) ||
            doc.description.toLowerCase().includes(searchLower);

          // Apply status filter
          const matchesStatus =
            selectedStatuses.value.length === 0 ||
            selectedStatuses.value.includes(doc.status);

          return matchesSearch && matchesStatus;
        })
        .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt)); // Sort by latest update
    });

    const fetchGroupNames = async () => {
      try {
        const response = await authService.getGroupNames();
        groupNames.value = response.data;
      } catch (error) {
        console.error("Error fetching group names:", error);
      }
    };

    const fetchUsername = async (userId) => {
      if (!usernames.value[userId]) {
        try {
          const username = await authService.getUserUsername(userId);
          usernames.value[userId] = username;
        } catch (error) {
          console.error(`Error fetching username for ${userId}:`, error);
          usernames.value[userId] = userId;
        }
      }
      return usernames.value[userId];
    };

    const mapStatus = (status) => {
      const statusMap = {
        draft: "Draft",
        pending_review: "Pending Review",
        published: "Published",
        rejected: "Rejected",
      };
      return statusMap[status?.toLowerCase()] || status;
    };

    const getStatusClass = (status) => {
      const mappedStatus = mapStatus(status);
      const classes = {
        Draft: "bg-gray-600 text-gray-100",
        "Pending Review": "bg-yellow-600 text-yellow-100",
        Published: "bg-green-600 text-green-100",
        Rejected: "bg-red-600 text-red-100",
      };
      return classes[mappedStatus] || "bg-gray-600 text-gray-100";
    };

    const fetchDocuments = async () => {
      try {
        const response = await documentService.getAllDocuments();
        documents.value = response.data;
      } catch (error) {
        console.error("Error fetching documents:", error);
      }
    };

    const submitForReview = async (docId) => {
      const doc = documents.value.find((d) => d.id === docId);
      if (!doc) return;

      selectedDocumentId.value = docId;
      selectedGroupId.value = doc.realmId;
      showSubmitModal.value = true;
    };

    const editDocument = (docId) => {
      if (!docId) {
        console.error("No document ID provided");
        return;
      }
      router.push(`/editor/${docId}`);
    };

    const reviewDocument = (docId) => {
      if (!docId) {
        console.error("No document ID provided");
        return;
      }
      router.push(`/review/${docId}`);
    };

    const viewDocument = (docId) => {
      if (!docId) {
        console.error("No document ID provided");
        return;
      }
      router.push(`/viewer/${docId}`);
    };

    const createNewVersion = async (docId) => {
      if (!docId) {
        console.error("No document ID provided");
        return;
      }
      try {
        const response = await documentService.createDocument({
          originalId: docId,
          type: "new_version",
        });
        router.push(`/editor/${response.data.id}`);
      } catch (error) {
        console.error("Error creating new version:", error);
      }
    };

    const createDocument = async () => {
      try {
        const response = await documentService.createDocument({
          title: newDocument.value.title,
          description: newDocument.value.description,
          realmId: newDocument.value.realmId,
        });

        showCreateModal.value = false;
        if (response.data && response.data.id) {
          router.push(`/editor/${response.data.id}`);
          // Reset form
          newDocument.value = {
            title: "",
            description: "",
            realmId: "",
          };
        }
      } catch (error) {
        console.error("Error creating document:", error);
        // You might want to show an error message to the user here
      }
    };

    const fetchAllUsers = async () => {
      try {
        const response = await authService.getAllUsers();
        allUsers.value = response.data;
      } catch (error) {
        console.error("Error fetching users:", error);
      }
    };

    const getAdminGroups = () => {
      try {
        const token = authStore.token;
        if (!token) return [];

        const payload = JSON.parse(atob(token.split(".")[1]));
        const realmRoles = payload.realm_roles || {};

        return Object.entries(realmRoles)
          .filter(([id, roles]) => roles.includes("admin"))
          .map(([id, roles]) => ({
            id,
            name: groupNames.value[id] || `Group ${id}`,
            roles,
          }));
      } catch (error) {
        console.error("Error parsing admin groups:", error);
        return [];
      }
    };

    const selectedGroupChanged = () => {
      // Reset roles when group changes
      roleAssignment.value.roles = [];
    };

    const createUser = async () => {
      try {
        await authService.createUser(newUser.value);
        showAddUserModal.value = false;
        newUser.value = {
          username: "",
          password: "",
          global_role: "user",
        };
        await fetchAllUsers();
      } catch (error) {
        console.error("Error creating user:", error);
        notificationService.error(
          "Failed to create user: " +
            (error.response?.data?.detail || "Unknown error")
        );
      }
    };

    const assignUserRole = async () => {
      try {
        await authService.assignGroupRoles(roleAssignment.value);
        showAssignRoleModal.value = false;
        roleAssignment.value = {
          username: "",
          group_name: "",
          roles: [],
        };
      } catch (error) {
        console.error("Error assigning role:", error);
        notificationService.error(
          "Failed to assign role: " +
            (error.response?.data?.detail || "Unknown error")
        );
      }
    };

    const createGroup = async () => {
      try {
        // Call the API with just the group name string
        await authService.createGroup(newGroup.value.group_name);
        showAddGroupModal.value = false;
        newGroup.value = {
          group_name: "",
        };
        // Refresh groups data
        await fetchGroupNames();
        userGroups.value = getUserGroups();
        adminGroups.value = getAdminGroups();
      } catch (error) {
        console.error("Error creating group:", error);
        notificationService.error(
          "Failed to create group: " +
            (error.response?.data?.detail || "Unknown error")
        );
      }
    };

    const isGlobalAdmin = computed(() => {
      try {
        const token = authStore.token;
        if (!token) return false;

        const payload = JSON.parse(atob(token.split(".")[1]));
        return payload.global_role === "admin";
      } catch (error) {
        console.error("Error checking global admin status:", error);
        return false;
      }
    });

    // Add this computed property before the return statement
    const hasAnyGroupAdminRole = computed(() => {
      try {
        const token = authStore.token;
        if (!token) return false;

        const payload = JSON.parse(atob(token.split(".")[1]));
        const realmRoles = payload.realm_roles || {};

        return Object.values(realmRoles).some((roles) =>
          roles.includes("admin")
        );
      } catch (error) {
        console.error("Error checking group admin roles:", error);
        return false;
      }
    });

    const handleReviewSubmitted = async () => {
      await fetchDocuments();
    };

    const formatDate = (dateString) => {
      const date = new Date(dateString);
      const now = new Date();
      const diff = now - date + date.getTimezoneOffset() * 60000;

      // Convert to minutes
      const minutes = Math.floor(diff / 60000);

      if (minutes < 1) {
        return "just now";
      }

      if (minutes < 60) {
        return `${minutes} minute${minutes > 1 ? "s" : ""} ago`;
      }

      const hours = Math.floor(minutes / 60);
      if (hours < 24) {
        return `${hours} hour${hours > 1 ? "s" : ""} ago`;
      }

      const days = Math.floor(hours / 24);
      if (days < 7) {
        return `${days} day${days > 1 ? "s" : ""} ago`;
      }

      const adjustedDate = new Date(
        date.getTime() - date.getTimezoneOffset() * 60000
      );

      return (
        "on " +
        adjustedDate.toLocaleDateString("en-US", {
          year: "numeric",
          month: "long",
          day: "numeric",
        })
      );
    };

    const isAdmin = (realmId) => {
      try {
        const token = authStore.token;
        if (!token) return false;

        const payload = JSON.parse(atob(token.split(".")[1]));
        const realmRoles = payload.realm_roles || {};

        // Check if user has admin role in this realm
        return realmRoles[realmId]?.includes("admin") || false;
      } catch (error) {
        console.error("Error checking admin status:", error);
        return false;
      }
    };

    const adminAction = (docId) => {
      if (!docId) {
        console.error("No document ID provided for admin action");
        return;
      }

      console.log("Opening admin panel for document:", docId);
      router.push(`/admin/${docId}`);
    };

    // Update onMounted to fetch group names
    onMounted(async () => {
      if (isLoggedIn.value) {
        await Promise.all([
          fetchGroupNames(),
          fetchDocuments(),
          fetchAllUsers(),
        ]);
        userGroups.value = getUserGroups();
        adminGroups.value = getAdminGroups();
        for (const doc of documents.value) {
          await fetchUsername(doc.creatorId);
        }
      }
    });

    const getUserGroups = () => {
      try {
        const token = authStore.token;
        if (!token) return [];

        const payload = JSON.parse(atob(token.split(".")[1]));
        const realmRoles = payload.realm_roles || {};

        return Object.entries(realmRoles).map(([id, roles]) => ({
          id,
          name: groupNames.value[id] || `Group ${id}`,
          roles,
        }));
      } catch (error) {
        console.error("Error parsing user groups:", error);
        return [];
      }
    };

    const getCurrentUserId = () => {
      try {
        const token = authStore.token;
        if (!token) return null;
        const payload = JSON.parse(atob(token.split(".")[1]));
        return payload.uid;
      } catch (error) {
        console.error("Error getting current user ID:", error);
        return null;
      }
    };

    const beforeEnter = (el) => {
      el.style.opacity = 0;
      el.style.transform = "translateY(10px)";
    };

    const enter = (el, done) => {
      setTimeout(() => {
        el.style.opacity = 1;
        el.style.transform = "translateY(0)";
        el.addEventListener("transitionend", done);
      }, el.dataset.index * 50);
    };

    const leave = (el, done) => {
      el.style.opacity = 0;
      el.style.transform = "translateY(10px)";
      el.addEventListener("transitionend", done);
    };

    return {
      isLoggedIn,
      isReviewer,
      documents,
      usernames,
      getStatusClass,
      mapStatus,
      submitForReview,
      editDocument,
      reviewDocument,
      viewDocument,
      createNewVersion,
      showCreateModal,
      newDocument,
      createDocument,
      userGroups,
      formatDate,
      groupNames,
      fetchUsername,
      showSubmitModal,
      selectedDocumentId,
      selectedGroupId,
      handleReviewSubmitted,
      getCurrentUserId,
      searchQuery,
      statusFilters,
      filteredDocuments,
      toggleStatusFilter,
      selectedStatuses,
      isAdmin,
      adminAction,
      showAddUserModal,
      createUser,
      roleAssignment,
      assignUserRole,
      showAssignRoleModal,
      allUsers,
      adminGroups,
      newUser,
      newGroup,
      beforeEnter,
      enter,
      leave,
      showAddGroupModal,
      newGroup,
      createGroup,
      isGlobalAdmin,
      hasAnyGroupAdminRole,
      selectedGroupChanged,
    };
  },
};
</script>

<style>
/* Add your custom styles here */

/* Staggered fade transition */
.staggered-fade-enter-active,
.staggered-fade-leave-active {
  transition: opacity 0.5s, transform 0.5s;
}

.staggered-fade-enter,
.staggered-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

/* Add smooth slide animations when items change position */
.staggered-fade-move {
  transition: transform 0.5s ease;
  position: relative;
  z-index: 1;
}

/* Make sure items maintain their space in the grid during transitions */
.staggered-fade-leave-active {
  position: absolute;
  opacity: 0;
  z-index: 0;
}
</style>
